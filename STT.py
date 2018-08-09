'''
    This version allows user to interact with
    custom models.
'''


#
# Copyright IBM Corp. 2014
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# Author: Daniel Bolanos
# Date:   2015


'''
	Changed by: Muhammad Umair
                Tufts University
	Date: July 2018

	The following modifications were made:

	1. Program does not accept inputs from text file.
	2. Program outputs to the current directory instead 
		of creating an output directory.
	3. Program takes an additional required names argument.
	4. Program outputs a CSV file for the two speakers 
		instea of JSON file.
	5. Only two threads can be run at a time.
	6. Std output format has been changed.
    7. Several Post-processing functions have been added.
    8. Included a seperate python script acting as a user 
        model interface.
'''

import json                        # json
import threading                   # multi threading
import os                          # for listing directories
import Queue                       # queue used for thread syncronization
import sys                         # system calls
import argparse                    # for parsing arguments
import base64                      # necessary to encode in base64
#                                  # according to the RFC2045 standard
import requests                    # python HTTP requests library
import itertools
import csv
from operator import itemgetter
import io
from custom_model import custom_model           # Required for custom model-user interface.
from subprocess import call
import time

# WebSockets
from autobahn.twisted.websocket import WebSocketClientProtocol, \
    WebSocketClientFactory, connectWS
from twisted.python import log
from twisted.internet import ssl, reactor

try:
    raw_input          # Python 2
except NameError:
    raw_input = input  # Python 3


# Global Variables.
JSON1 = []
JSON2 = []


class Utils:

    @staticmethod
    def getAuthenticationToken(hostname, serviceName, username, password):

        fmt = hostname + "{0}/authorization/api/v1/token?url={0}/{1}/api"
        uri = fmt.format(hostname, serviceName)
        uri = uri.replace("wss://", "https://").replace("ws://", "https://")
        print(uri)
        auth = (username, password)
        headers = {'Accept': 'application/json'}
        resp = requests.get(uri, auth=auth, verify=False, headers=headers,
                            timeout=(30, 30))
        print(resp.text+"\n")
        jsonObject = resp.json()
        return jsonObject['token']


class WSInterfaceFactory(WebSocketClientFactory):

    def __init__(self, queue, summary, dirOutput, contentType, model,
                url=None, headers=None, debug=None):

        WebSocketClientFactory.__init__(self, url=url, headers=headers)
        self.queue = queue
        self.summary = summary
        self.dirOutput = dirOutput
        self.contentType = contentType
        self.model = model
        self.queueProto = Queue.Queue()

        self.openHandshakeTimeout = 10
        self.closeHandshakeTimeout = 10

        # start the thread that takes care of ending the reactor so
        # the script can finish automatically (without ctrl+c)
        endingThread = threading.Thread(target=self.endReactor, args=())
        endingThread.daemon = True
        endingThread.start()

    def prepareUtterance(self):

        try:
            utt = self.queue.get_nowait()
            self.queueProto.put(utt)
            return True
        except Queue.Empty:
            print("getUtterance: no more utterances to process, queue is "
                  "empty!")
            return False

    def endReactor(self):

        self.queue.join()
        print("about to stop the reactor!")
        reactor.stop()

    # this function gets called every time connectWS is called (once
    # per WebSocket connection/session)
    def buildProtocol(self, addr):

        try:
            utt = self.queueProto.get_nowait()
            proto = WSInterfaceProtocol(self, self.queue, self.summary,
                                        self.dirOutput, self.contentType)
            proto.setUtterance(utt)
            return proto
        except Queue.Empty:
            print("queue should not be empty, otherwise this function should "
                  "not have been called")
            return None

# Saves the json transcripts to global variables
def save_var(json1, json2):
	global JSON1
	global JSON2
	JSON1 = json1
	JSON2 = json2

# WebSockets interface to the STT service
#
# note: an object of this class is created for each WebSocket
# connection, every time we call connectWS
class WSInterfaceProtocol(WebSocketClientProtocol):

    def __init__(self, factory, queue, summary, dirOutput, contentType):
        self.factory = factory
        self.queue = queue
        self.summary = summary
        self.dirOutput = dirOutput
        self.contentType = contentType
        self.packetRate = 20
        self.listeningMessages = 0
        self.timeFirstInterim = -1
        self.bytesSent = 0
        self.chunkSize = 2000     # in bytes
        self.json_output = []
        super(self.__class__, self).__init__()
        print("Output Directory: " +dirOutput + "\n")
        print("contentType: {} queueSize: {}".format(self.contentType,
                                                     self.queue.qsize()))

    # Class Variables
    num = 0
    JSON1 = []
    JSON2 = []

    def setUtterance(self, utt):

        self.uttNumber = utt[0]
        self.uttFilename = utt[1]
        self.summary[self.uttNumber] = {"hypothesis": "",
                                        "status": {"code": "", "reason": ""}}
        self.fileJson = "{}/{}.json.txt".format(self.dirOutput, self.uttNumber)

    # helper method that sends a chunk of audio if needed (as required
    # what the specified pacing is)
    def maybeSendChunk(self, data):

        def sendChunk(chunk, final=False):
            self.bytesSent += len(chunk)
            self.sendMessage(chunk, isBinary=True)
            if final:
                self.sendMessage(b'', isBinary=True)

        if (self.bytesSent + self.chunkSize >= len(data)):
            if (len(data) > self.bytesSent):
                sendChunk(data[self.bytesSent:len(data)], True)
                return
        sendChunk(data[self.bytesSent:self.bytesSent + self.chunkSize])
        self.factory.reactor.callLater(0.01, self.maybeSendChunk, data=data)
        return

    def onConnect(self, response):
        print("onConnect, server connected: {}".format(response.peer))

    def onOpen(self):
        print("Opening API Connection")
        data = {"action": "start",
                "content-type": str(self.contentType),
                "continuous": True,
                "interim_results": True,
                "inactivity_timeout": 600,
                'max_alternatives': 3,
                'timestamps': True,
                'word_confidence': True}


        #print("sendMessage(init)")
        # send the initialization parameters
        self.sendMessage(json.dumps(data).encode('utf8'))

        # start sending audio right away (it will get buffered in the
        # STT service)
        print(self.uttFilename)
        with open(str(self.uttFilename), 'rb') as f:
            self.bytesSent = 0
            dataFile = f.read()
        self.maybeSendChunk(dataFile)


    def onMessage(self, payload, isBinary):

            # if uninitialized, receive the initialization response
            # from the server
            jsonObject = json.loads(payload.decode('utf8'))
            if 'state' in jsonObject:
                self.listeningMessages += 1
                if self.listeningMessages == 2:
                    print("sending close 1000")
                    # close the connection
                    self.sendClose(1000)

            # if in streaming
            elif 'results' in jsonObject:
                jsonObject = json.loads(payload.decode('utf8'))
                hypothesis = ""
                # empty hypothesis
                if len(jsonObject['results']) == 0:
                    print("empty transcription!")
                # regular hypothesis
                else:
                    # dump the message to the output directory
                    jsonObject = json.loads(payload.decode('utf8'))
                    self.json_output.append(jsonObject)
                    res = jsonObject['results'][0]
                    hypothesis = res['alternatives'][0]['transcript']
                    bFinal = (res['final'] is True)
                    if bFinal:
                        print('Final transcription: "' + hypothesis + '"')
                        self.summary[self.uttNumber]['hypothesis'] += hypothesis
                    else:
                        pass

    def onClose(self, wasClean, code, reason):

        print("Closing API Connection")
        print("WebSocket connection closed: {0}, code: {1}, clean: {2}, "
              "reason: {0}".format(reason, code, wasClean))
        self.summary[self.uttNumber]['status']['code'] = code
        self.summary[self.uttNumber]['status']['reason'] = reason

        if WSInterfaceProtocol.num == 0:
        	WSInterfaceProtocol.JSON1 = self.json_output
        	WSInterfaceProtocol.num += 1
        elif WSInterfaceProtocol.num == 1:
        	WSInterfaceProtocol.JSON2 = self.json_output
        	WSInterfaceProtocol.num+=1
        	save_var(WSInterfaceProtocol.JSON1,WSInterfaceProtocol.JSON2)

        # create a new WebSocket connection if there are still
        # utterances in the queue that need to be processed
        self.queue.task_done()

        if not self.factory.prepareUtterance():
            return

        # SSL client context: default
        if self.factory.isSecure:
            contextFactory = ssl.ClientContextFactory()
        else:
            contextFactory = None
        connectWS(self.factory, contextFactory)



# function to check that a value is a positive integer
def check_positive_int(value):
    ivalue = int(value)
    if ivalue < 1:
        raise argparse.ArgumentTypeError(
            '"%s" is an invalid positive int value' % value)
    return ivalue


# function to check the credentials format
def check_credentials(credentials):
    elements = credentials.split(":")
    if len(elements) == 2:
        return elements
    else:
        raise argparse.ArgumentTypeError(
            '"%s" is not a valid format for the credentials ' % credentials)


# Function that creates seperate CSV files for both speakers.
def build_seperate_CSV(json1,json2,name1,name2):
    new_json1 = []
    new_json2 = []

    for item in json1:
        if item['results'][0]['final'] == True:
            new_json1.append(item)

    for item in json2:
        if item['results'][0]['final'] == True:
            new_json2.append(item)

    # Creating thr json files for reference
    with open('json3.txt', "w") as f:
        f.write(json.dumps(new_json1, indent=4,
                 sort_keys=True))
    with open('json4.txt',"w") as f:
        f.write(json.dumps(new_json2,indent = 4,
                sort_keys = True))
    with open('json3.txt') as speaker1_data:
        speaker1_result = json.load(speaker1_data)
    with open('json4.txt') as speaker2_data:
        speaker2_result = json.load(speaker2_data)

    # Initializing
    all_lines1 = []
    all_lines2 = []

    data1 = []
    for item in speaker1_result:
        sub_item = item['results'][0]['alternatives'][0]['timestamps']
        for subdata in sub_item:
            data1.append(subdata)

    data2 = []
    for item in speaker2_result:
        sub_item = item['results'][0]['alternatives'][0]['timestamps']
        for subdata in sub_item:
            data2.append(subdata)

    for res1 in data1:
        trans1 = " "+res1[0]+" "
        start1 = res1[1]
        end1 = res1[2]
        all_lines1.append([name1,start1,end1,trans1])

    for res2 in data2:
        trans2 = " "+res2[0]+" "
        start2 = res2[1]
        end2 = res2[2]
        all_lines2.append([name2,start2,end2,trans2])

    # Removing the json files
    try:
        os.remove('json3.txt')
        os.remove('json4.txt')
    except OSError:
        pass

    final = [all_lines1,all_lines2]

    return final




# Function to write to the CSV file
def writeCSV(all_lines,name):
	# Writing to the CSV file
	with open(name,"wb") as csvfile:
    		filewriter = csv.writer(csvfile, delimiter=',',
	                          	quotechar='|', quoting=csv.QUOTE_MINIMAL)
    		for line in all_lines:
    			filewriter.writerow(line)


# Function that does pos-processing on the seperate 
# speaker CSV files.
def seperate_postprocessing(all_lines):
    all_lines = create_utterances(all_lines,0.1)
    return all_lines


# Function that creates utterances based on a threshold for
# the individual speakers.
def create_utterances(all_lines,threshold):
    new_lines = []
    count = 0
    new = True
    changed = False
    while count < len(all_lines)-1:
        #print(count)
        #print(all_lines[count])
        #print(all_lines[count+1])
        curr_end = all_lines[count][2]
        nxt_start = all_lines[count+1][1]
        diff = nxt_start - curr_end
        #print('diff')
        #print(diff)
        if diff <= threshold or diff == 0:
            changed = True
            #print('changing')
            new_trans = all_lines[count][-1]+u''+all_lines[count+1][-1]
            all_lines[count][-1] = new_trans
            all_lines[count][2] = all_lines[count+1][2]
            if len(new_lines) > 0  and len(new_lines[-1][-1].split()) > 1:
                print('overwiriting')
                new_lines[-1] = [all_lines[count][0],all_lines[count][1],all_lines[count+1][2],new_trans]
            else:
                #print('appending')
                new_lines.append([all_lines[count][0],all_lines[count][1],all_lines[count+1][2],new_trans])
            #print(new_lines[-1])
            del all_lines[count+1]
            if count >= len(all_lines):
                return new_lines
        else:
            #print('Not adding')
            if  changed ==  False:
                new_lines.append(all_lines[count])
            else:
                new_lines.append(all_lines[count+1])
            #print(new_lines[-1])
            count+=1
       # print('\n')
    return new_lines



# Function that combines and does postprocessing on
# the two seperately created CSV files
def combined_postprocessing(data1,data2):

    all_lines = combined_concat(data1,data2)
    all_lines = extra_spaces(all_lines)
    all_lines = overlaps(all_lines)
    all_lines = pauses(all_lines)
    all_lines = combined_same_concat(all_lines)
    all_lines = eol_delim(all_lines)
    all_lines = rem_pause_ID(all_lines)
    all_lines = comment_hesitation(all_lines)
    all_lines = gaps(all_lines)
    all_lines = extra_spaces(all_lines)
    all_lines = extra_spaces(all_lines)

    return all_lines

    all_lines = combined_concat(data1,data2)
    all_lines = pauses(all_lines)
    all_lines = extra_spaces(all_lines)
    all_lines = combined_same_concat(all_lines)
    all_lines = overlaps(all_lines)
    all_lines = eol_delim(all_lines)
    all_lines = rem_pause_ID(all_lines)
    all_lines = comment_hesitation(all_lines)
    all_lines = gaps(all_lines)

    return all_lines


# Function that adds gaps
# Should be used as the last postprocessing function
def gaps(all_lines):
    count = 0
    while count < len(all_lines):
        curr_item = all_lines[count]
        prev_item = all_lines[count-1]
        curr_start = curr_item[1]
        prev_end = prev_item[2]
        prev_trans = prev_item[-1]
        curr_name = curr_item[0]
        prev_name = prev_item[0]
        curr_trans = curr_item[-1]
        if count > 1:
            second_last_end = all_lines[count-2][2]
        else:
            second_last_end = curr_start
        if second_last_end == None:
            second_last_end = curr_start
        if count < 0:
            prev_end = curr_start
        if prev_end == None:
            prev_end = curr_start
        #print('cuur_start ',curr_start)
        #print('second last end ', second_last_end)
        #print('prev_end ', prev_end)
        if second_last_end > prev_end:
            #print('changing')
            prev_end = second_last_end
            #print('prev_end changed ', prev_end)
        diff = curr_start - prev_end
        diff = round(diff,1)
        #print('diff ', diff)
        #print('\n')
        if curr_name != prev_name and curr_name != '*PPP':
            # Normal gap
            if diff > 0.3:
                new_item = [' ', prev_end , curr_start , '\t('+str(diff)+') . ']
                all_lines.insert(count,new_item)
                pos = prev_trans.rfind('.')
                if pos != -1:
                    if prev_trans[pos+1].isnumeric() == False or prev_trans[pos+1] != ')':
                        prev_trans = prev_trans[:pos-1]+prev_trans[pos+1:]
                all_lines[count-1][-1] = prev_trans
                count+=1
            # Adding the latch markers
            elif diff > 0.01 and diff < 0.05: 
                pos = prev_trans.rfind('.')
                prev_trans = prev_trans[:pos-1]+u' '+u"^"+u' '+prev_trans[pos:]
                all_lines[count-1][-1] = prev_trans
                curr_trans = u'^ '+curr_trans
                all_lines[count][-1] = curr_trans

        count +=1
    return all_lines

# Function that changed places the hesitation marker
# within comments
def comment_hesitation(all_lines):
    for items in all_lines:
        trans = items[-1]
        items[-1] = trans.replace("%HESITATION", "[^ %HESITATION ] ")
    all_lines = sorted(all_lines, key = itemgetter(1))
    return all_lines

# Function that adds overlap markers based on time
# Meant for combined post-processing
# Modified so that this no longer adds overlap markers
# if only one character from any of the utterances 
# is modified
def overlaps(all_lines):
    count = 0
    limit = 1
    while count <  len(all_lines)-1:
        all_lines[count][-1] = all_lines[count][-1].lstrip()
        all_lines[count+1][-1] = all_lines[count+1][-1].lstrip()
        all_lines[count][-1] = all_lines[count][-1].rstrip()
        all_lines[count+1][-1] = all_lines[count+1][-1].rstrip()
        if all_lines[count][0] != all_lines[count+1][0] and all_lines[count+1][0] != '*PPP':
            # Checking for overlap
            if all_lines[count+1][1] < all_lines[count][2]:
                start_boundary_time = all_lines[count+1][1] - all_lines[count][1]
                end_boundry_time  = all_lines[count][2] - all_lines[count+1][2]
                #print(start_boundary_time,end_boundry_time)
                #print('\n')



                # Case 1:
                # sbt is positive means overlap starts at position x from start of 
                # utterance 1 but at the start of utterance 2
                if start_boundary_time > 0:
                   # print('start > 0')
                    x = (abs(start_boundary_time)/(all_lines[count][2]-all_lines[count][1]))*100
                    x = (x/100)*len(all_lines[count][-1])
                    x = int(round(x))
                    #print('x: ',x)
                    utt_1_overlap_start = x
                    orig1 = all_lines[count][-1]
                    orig2 = all_lines[count+1][-1]
                    all_lines[count][-1] = all_lines[count][-1][:utt_1_overlap_start]+'<'+all_lines[count][-1][utt_1_overlap_start:]
                    all_lines[count+1][-1] = '<'+all_lines[count+1][-1]

                    # Case 1 a: 
                        # ebt is positive means that overlap ends at position y from 
                        # utterance one start and overlaps end at end position of 
                        # utterance 2
                    if end_boundry_time > 0:
                        #print('end > 0')
                        y = 100-((abs(end_boundry_time))/(all_lines[count][2]-all_lines[count][1])*100)
                        y = (y/100)*len(all_lines[count][-1])
                        y = int(round(y))
                        utt_1_overlap_end = y
                        # Adding the overlap character limit
                        if utt_1_overlap_end - utt_1_overlap_start <= limit:
                            print('removing marker')
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        #print('y: ',y)
                        all_lines[count][-1] = all_lines[count][-1][:utt_1_overlap_end]+'> [>] '+all_lines[count][-1][utt_1_overlap_end:]
                        all_lines[count+1][-1] = all_lines[count+1][-1]+'> [<] '

                    # Case 1 b:
                        # ebt is negative means that overlap ends at utterance 1 end
                        # and that overlap ends at position y from utterance 2 end.
                    elif end_boundry_time < 0:
                        #print('end < 0')
                        y = 100-((abs(end_boundry_time)/(all_lines[count+1][2]-all_lines[count+1][1]))*100)
                        y = (y/100)*len(all_lines[count+1][-1])
                        y = int(round(y))
                        utt_2_overlap_end = y 
                        # Adding the overlap character limit
                        if len(all_lines[count][-1])-utt_1_overlap_start <= limit:
                            print('removing marker')
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        if utt_2_overlap_end - 0 <= limit:
                            print('removing marker')
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        #print('y: ',y)
                        all_lines[count][-1] = all_lines[count][-1]+'> [>] '
                        all_lines[count+1][-1] = all_lines[count+1][-1][:utt_2_overlap_end]+'> [<] '+all_lines[count+1][-1][utt_2_overlap_end:]
                        #print(y)

                    # Case 1 c:
                        # ebt is 0 means that the overlap ends at both utterances end
                    elif end_boundry_time == 0:
                        #print('end == 0')
                        all_lines[count][-1] = all_lines[count][-1] + '> [>] '
                        all_lines[count+1][-1] = all_lines[count+1][-1] +'> [<] '

                # Case 2:
                # Sbt is negative means that overlap starts from start of utterance 1
                # and position x  of utterance 2.
                elif start_boundary_time < 0:
                    #print('start < 0')
                    x = (abs(start_boundary_time)/(all_lines[count+1][2]-all_lines[count+1][1]))*100
                    x = (x/100)*len(all_lines[count+1][-1])
                    x = int(round(x))
                    #print('x: ',x)
                    utt_2_overlap_start = x
                    orig1 = all_lines[count][-1]
                    orig2 = all_lines[count+1][-1]
                    all_lines[count][-1] = '<'+all_lines[count][-1]
                    all_lines[count+1][-1] = all_lines[count+1][-1][:utt_2_overlap_start]+'<'+all_lines[count+1][-1][utt_2_overlap_start:]

                    # Case 2 a: 
                        # ebt is positive means that overlap ends at position y from 
                        # utterance one start and overlaps end at end position of 
                        # utterance 2
                    if end_boundry_time > 0:
                        #print('end > 0')
                        y = 100-((abs(end_boundry_time)/(all_lines[count][2]-all_lines[count][1]))*100)
                        y = (y/100)*len(all_lines[count][-1])
                        y = int(round(y))
                        utt_1_overlap_end = y
                        if utt_1_overlap_end - 0 <= limit:
                            print('removing marker')
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        if len(all_lines[count+1][-1])-utt_2_overlap_start <= limit:
                            print('removing marker')
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        #print('y: ',y)
                        all_lines[count][-1] = all_lines[count][-1][:utt_1_overlap_end]+'> [>] '+all_lines[count][-1][utt_1_overlap_end:]
                        all_lines[count+1][-1] = all_lines[count+1][-1]+'> [<] '


                    # Case 2 b:
                        # ebt is negative means that overlap ends at utterance 1 end
                        # and that overlap ends at position y from utterance 2 end.
                    elif end_boundry_time < 0:
                        #print('end < 0')
                        y = 100-((abs(end_boundry_time)/(all_lines[count+1][2]-all_lines[count+1][1]))*100)
                        y = (y/100)*len(all_lines[count+1][-1])
                        y = int(round(y))
                        utt_2_overlap_end = y
                        if utt_2_overlap_end- utt_2_overlap_start <= limit:
                            print('removing marker')
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        #print('y: ',y)
                        all_lines[count][-1] = all_lines[count][-1]+'> [>] '
                        all_lines[count+1][-1] = all_lines[count+1][-1][:utt_2_overlap_end]+'> [<] '+all_lines[count+1][-1][utt_2_overlap_end:]

                    # Case 2 c:
                        # ebt is 0 means that overlap ends at both utterances end.
                    elif end_boundry_time == 0:
                        #print('end == 0')
                        all_lines[count][-1] = all_lines[count][-1] + '> [>] '
                        all_lines[count+1][-1] = all_lines[count+1][-1] +'> [<] '

                # Case 3: 
                # sbt is 0 means that the overlap starts from the start of both turns.
                elif start_boundary_time == 0:
                    #print('start == 0')
                    orig1 = all_lines[count][-1]
                    orig2 = all_lines[count+1][-1]
                    all_lines[count][-1] = '<'+all_lines[count][-1]
                    all_lines[count+1][-1] = '<'+all_lines[count+1][-1]

                    # Case 3 a: 
                        # ebt is positive means that overlap ends at position y from 
                        # utterance one start and overlaps end at end position of 
                        # utterance 2
                    if end_boundry_time > 0:
                        #print('end > 0')
                        y = 100-((abs(end_boundry_time)/(all_lines[count][2]-all_lines[count][1]))*100)
                        y = (y/100)*len(all_lines[count][-1])
                        y = int(round(y))
                        utt_1_overlap_end = y
                        if utt_1_overlap_start - 0 <= limit:
                            print('removing marker')
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        #print('y: ',y)
                        all_lines[count][-1] = all_lines[count][-1][:utt_1_overlap_end]+'> [>] '+all_lines[count][-1][utt_1_overlap_end:]
                        all_lines[count+1][-1] = all_lines[count+1][-1]+'> [<] '

                    # Case 3 b:
                        # ebt is negative means that overlap ends at utterance 1 end
                        # and that overlap ends at position y from utterance 2 end.
                    elif end_boundry_time < 0:
                        #print('end < 0')
                        y = 100-((abs(end_boundry_time)/(all_lines[count+1][2]-all_lines[count+1][1]))*100)
                        y = (y/100)*len(all_lines[count+1][-1])
                        y = int(round(y))
                        utt_2_overlap_end = y
                        if utt_2_overlap_end - 0 <= limit:
                            print('removing marker')
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        #print('y: ',y)
                        all_lines[count][-1] = all_lines[count][-1]+'> [>] '
                        all_lines[count+1][-1] = all_lines[count+1][-1][:utt_2_overlap_end]+'> [<] '+all_lines[count+1][-1][utt_2_overlap_end:]

                    # Case 3 c:
                        # ebt is 0 means that overlap ends at both utterances end.
                    elif end_boundry_time == 0:
                        #print('end == 0')
                        all_lines[count][-1] = all_lines[count][-1] + '> [>] '
                        all_lines[count+1][-1] = all_lines[count+1][-1] +'> [<] ' 
                count+=1
            else:
                count+=1

        elif all_lines[count+1][0] == '*PPP':
            count+=2
        elif all_lines[count][0] == all_lines[count+1][0]:
            count+=1


    # Moving overlaps out of pause markers
    for item in all_lines:
        trans = item[-1]
        new_trans = ''
        count = 0
        while count < len(trans):
            if trans[count] == '(':
                pause_marker = ''
                overlap_marker = ''
                while trans[count] != ')':
                    if trans[count] != '>' and trans[count] != '<' and trans[count] != '[' and trans[count] != ']' and trans[count] != ' ':
                        pause_marker += trans[count]
                    else:
                        overlap_marker += trans[count]
                        #print(overlap_marker)
                    count+=1
                #print(pause_marker)
                new_trans += overlap_marker
                new_trans += pause_marker+')'
               #print(overlap_marker)
            else:
                new_trans += trans[count]

            count+=1
        #print(new_trans)
        #print(item[-1])
        #print('\n')
        item[-1] = new_trans



    # Moving overlap marker behind pause if it exists
    for item in all_lines:
        trans = item[-1]
        new_trans = ''
        count = 0
        marker = False
        while count < len(trans):
            if trans[count] == '<' and trans[count+1] != ']':
                new_trans += trans[count]
                marker = True
                count+=1
            elif marker == True and trans[count] == '(':
                pos = count
                pause = ''
                while trans[count] != ')':
                    pause += trans[count]
                    count+=1
                    if count >= len(trans):
                        break
                pause += ')'
                count+=1
                if count >= len(trans):
                    break
                extra = ''
                while trans[count] != '>':
                    extra+= trans[count]
                    count+=1
                    if count >= len(trans):
                        break
                overlap = ''
                if count >= len(trans):
                    break
                while trans[count] != ']':
                    overlap += trans[count]
                    count+=1
                    if count >= len(trans):
                        break
                overlap += ']'
                overlap+= ' '
                count+=2


                new_trans += overlap
                new_trans += pause
                new_trans += extra
                marker = False
            elif marker== True and trans[count] == '>':
                new_trans += trans[count]
                marker = False
                count+=1
            else:
                new_trans += trans[count]
                count+=1
        item[-1] = new_trans

    # Removing space padding from around the overlap markers
    for item in all_lines:
        trans = item[-1]
        count = 0
        new_trans = ''
        while count < len(trans):
            if trans[count] == '<' and trans[count+1] != ']':
                #new_trans += trans[count]
                count+=1
                overlapped = ''
                while trans[count] != '>':
                    overlapped += trans[count]
                    count+=1
                    if count >= len(trans):
                        break
                left_spaces = len(overlapped) - len(overlapped.lstrip(' '))
                for i in range(left_spaces):
                    new_trans += ' '
                new_trans += '<'
                overlapped = overlapped.lstrip()
                overlapped = overlapped.rstrip()
                new_trans += overlapped
                new_trans += '>'
                count+=1
            else:
                new_trans += trans[count]
                count+=1
        item[-1] = new_trans



    return all_lines









# Function that concatenates utterances 
# from two different speakers as part of the 
# combined post-processing.
def combined_concat(data1,data2):
    all_lines = []
    for res1,res2 in map(None,data1,data2):
        if res1 != None and res2 != None:
            trans1 = res1[-1]
            trans2 = res2[-1]
            start1 = res1[1]
            start2 = res2[1]
            end1 = res1[2]
            end2 = res2[2]
            name1 = res1[0]
            name2 = res2[0]
            trans1 = ' '+trans1
            trans2 = ' '+trans2
            #print(start1,start2)
            #print('\n')
            if start1 < start2:
                all_lines.append([name1,start1,end1,trans1])
                all_lines.append([name2,start2,end2,trans2])
            else:
                all_lines.append([name2,start2,end2,trans2])
                all_lines.append([name1,start1,end1,trans1])
        elif res1 == None and res2 != None:
            trans2 = res2[-1]
            start2 = res2[1]
            end2 = res2[2]
            name2 = res2[0]
            all_lines.append([name2,start2,end2,trans2])
        elif res1 != None and res2 == None:
            trans1 = res1[-1]
            start1 = res1[1]
            end1 = res1[2]
            name1 = res1[0]
            all_lines.append([name1,start1,end1,trans1])
    # Sorting by start time
    all_lines = sorted(all_lines, key= itemgetter(1))
    return all_lines


# Function that concatenates same speaker utterances
# Meant to be used in the combined post-processing stage.
def combined_same_concat(all_lines):
    count = 0
    while count < len(all_lines)-1:
        if all_lines[count][0] == all_lines[count+1][0]:
            new_trans = all_lines[count][-1]+all_lines[count+1][-1]
            if all_lines[count][-1][0] != ' ':
                all_lines[count][-1] = new_trans
            else:
                all_lines[count][-1] = new_trans
            all_lines[count][2] = all_lines[count+1][2]
            del all_lines[count+1]
        else:
            count+=1
    return all_lines

# Function that adds pauses
def pauses(all_lines):
    all_lines = sorted(all_lines, key = itemgetter(1))
    count = 0
    while count < len(all_lines):
        special = False
        curr_item = all_lines[count]
        prev_item = all_lines[count-1]
        curr_start = curr_item[1]
        prev_end = prev_item[2]
        prev_trans = prev_item[-1]
        curr_name = curr_item[0]
        prev_name = prev_item[0]
        if count > 1:
            second_last_end = all_lines[count-2][2]
        else:
            second_last_end = curr_start
        if second_last_end == None:
            second_last_end = curr_start
        if count < 0:
            prev_end = curr_start
        if prev_end == None:
            prev_end = curr_start
        #print('cuur_start ',curr_start)
        #print('second last end ', second_last_end)
        #print('prev_end ', prev_end)
        if second_last_end > prev_end:
            #print('changing')
            special = True
            #print('prev_end changed ', prev_end)
        diff = curr_start - prev_end
        diff = round(diff,1)
        #print('diff ', diff)
        #print('\n')
        if curr_name == prev_name:
            # Normal pause
            if (diff > 0.2 and diff < 2.5) or special == True:
                prev_trans += ' ('+str(diff)+') '
                all_lines[count-1][-1] = prev_trans
            # Micropauses
            elif diff > 0.1 and diff < 0.2:
                prev_trans += ' (.) '
                all_lines[count-1][-1] = prev_trans
            # Very large pauses
            elif diff > 2.5: 
                new_item = ['*PPP', prev_end , curr_start , '('+str(diff)+') ']
                all_lines.insert(count,new_item)
                pos = prev_trans.rfind('.')
                if pos != -1:
                    if prev_trans[pos+1].isnumeric() == False or prev_trans[pos+1] != ')':
                        prev_trans = prev_trans[:pos-1]+prev_trans[pos+1:]
                all_lines[count-1][-1] = prev_trans
        count +=1
    return all_lines

# Function that removes extra speaker ID as 
# part of the pause and gap functionality.
# **NOTE: Should be used at the end
# The end of line delimiters should be added before this 
# function.
def rem_pause_ID(all_lines):
    count = 0
    while count < len(all_lines):
        curr_item = all_lines[count]
        prev_item = all_lines[count-1]
        curr_start = curr_item[1]
        prev_end = prev_item[2]
        prev_trans = prev_item[-1]
        curr_name = curr_item[0]
        prev_name = prev_item[0]
        curr_trans = curr_item[-1]
        if prev_end == None:
            prev_end = curr_start
        if curr_name == '*PPP':
            curr_name = ''
            all_lines[count][0] = curr_name
            all_lines[count][-1] = '\t'+curr_trans
            pos = prev_trans.rfind('.')
            if pos != -1:
                if prev_trans[pos+1].isnumeric() == False or prev_trans[pos+1] != ')':
                    prev_trans = prev_trans[:pos-1]+prev_trans[pos+1:]
            all_lines[count-1][-1] = prev_trans
        count+=1
    return all_lines

# Function that adds end of utterance markers
def eol_delim(all_lines):
    if len(all_lines) > 0:
        for item in all_lines:
            item[-1] += " . "
    all_lines = sorted(all_lines, key = itemgetter(1))
    return all_lines

# Function that removes extra spaces
def extra_spaces(all_lines):
    for item in all_lines:
        trans = item[-1]
        count = 0
        new_trans = ""
        while count < len(trans):
            line = trans[count]
            if trans[count] == ' ' and trans[count-1] == ' ':
                line = ''
            count += 1
            new_trans += line
        item[-1] = new_trans
    all_lines = sorted(all_lines, key = itemgetter(1))
    return all_lines




# Function that builds a CHAT file from 
# data formatted for the CSV format
def build_CHAT(all_lines,name1,name2,audio_name):
    for item in all_lines:
        item = [unicode(x) for x in item]
    id1 = name1[:3].upper()
    id2 = name2[:3].upper()
    if id1 == id2:
        id1 = id1[:2]+'1'
        id2 = id2[:2]+'2'
    with io.open('combined.cha',"w",encoding = 'utf-8') as outfile:
        outfile.write(u'@Begin\n@Languages:\teng\n@Participants:\t')
        outfile.write(unicode(id1)+u' '+unicode(name1)+u' Unidentified, '+unicode(id2)+u' '+unicode(name2)+u' Unidentified\n')
        outfile.write(u'@Options:\tCA\n')
        outfile.write(u'@ID:\teng|In_Conversation_Corpus|'+unicode(id1)+'||male|||Unidentified|||'+'\n')
        outfile.write(u'@ID:\teng|In_Conversation_Corpus|'+unicode(id2)+'||male|||Unidentified|||'+'\n')
        outfile.write(u'@Media:\t'+unicode(audio_name)+u',audio\n')
        outfile.write(u'@Comment:\tIn_Conversation_Corpus, Hi_Lab\n')
        outfile.write(u'@Transcriber:\tSTT_system\n@Location:\tHI Lab\n@Room Layout:\tHi Lab duplex\n')
        outfile.write(u'@Situation:\tLaboratory\n@New Episode\n')
        for item in all_lines:
            name = item[0]
            start = int(item[1]*1000)
            end = int(item[2]*1000)
            trans = item[-1]
            if name == name1:
                outfile.write(u'*'+unicode(id1)+u':\t')
            elif name == name2:
                outfile.write(u'*'+unicode(id2)+u':\t')
            # For pauses
            elif name == '*PPP':
                outfile.write(name+u':\t')
            count = 0
            col = 0
            while count < len(trans):
                if trans[count] == ' ':
                    pos = count
                    pos += 1
                    if pos >= len(trans):
                        break
                    while trans[pos] != ' ':
                        pos += 1
                        if pos >= len(trans):
                            break
                    diff = pos - count
                    if (col + diff) >= 68 and trans[count-1] != '.':
                        if trans[count+1] != '[' and trans[count+1] != '>' and trans[count+1] != '<' and trans[count+1]!= ']':
                            outfile.write(u'\r')
                            outfile.write(u'\t')
                            col = 0
                #  Adding latch symbol.
                if trans[count] == '^' and trans[count-1] != '[':
                    outfile.write(u'\u2248')
                else:
                    outfile.write(unicode(trans[count]))
                count += 1
                col += 1
            outfile.write(' '+u'\u0015'+unicode(start)+u'_'+unicode(end)+u'\u0015')
            outfile.write(u'\n')
        outfile.write(u'@End\r')




if __name__ == '__main__':


    # parse command line parameters
    parser = argparse.ArgumentParser(
        description=('client to do speech recognition using the WebSocket '
                     'interface to the Watson STT service'))
    parser.add_argument(
        '-credentials', action='store', dest='credentials',
        help="Basic Authentication credentials in the form 'username:password'",
        required=True, type=check_credentials)
    parser.add_argument(
        '-in', action='store', dest='fileInput', default=None,
        help='text file containing audio files', required = False)
    parser.add_argument(
        '-out', action='store', dest='dirOutput', default='./',
        help='output directory', required = False)
    parser.add_argument(
        '-type', action='store', dest='contentType', default='audio/wav',
        help='audio content type, for example: \'audio/l16; rate=44100\'')
    parser.add_argument(
        '-model', action='store', dest='model', default='en-US_BroadbandModel',
        help='STT model that will be used')
    parser.add_argument(
        '-amcustom', action='store', dest='am_custom_id', default=None,
        help='id of the acoustic model customization that will be used', required=False)
    parser.add_argument(
        '-lmcustom', action='store', dest='lm_custom_id', default=None,
        help='id of the language model customization that will be used', required=False)
    parser.add_argument(
        '-threads', action='store', dest='threads', default='2',
        help='number of simultaneous STT sessions', type=check_positive_int)
    parser.add_argument(
        '-optout', action='store_true', dest='optOut',
        help=('specify opt-out header so user data, such as speech and '
              'hypotheses are not logged into the server'))
    parser.add_argument(
        '-tokenauth', action='store_true', dest='tokenauth',
        help='use token based authentication')
    parser.add_argument(
    	'-files', action = 'store' , dest = 'in_files', default = None,
    		help='Path to audio file', nargs = 2, required = True )
    parser.add_argument(
    	'-names', action = 'store', dest = 'Names',
    		help='Names of the speakers', nargs = 2, required = True)
    # Name of the combined audio file.
    parser.add_argument(
        '-audio',action = 'store', dest = 'combined_audio',
            nargs = 1, required = True)

    args = parser.parse_args()

    if args.fileInput != None:
    	print("This version does not allow file input")
    	print("Exiting...")
    	sys.exit()
    else:
    	lines = args.in_files

    # Checking if the files exist
    if os.path.isfile(args.in_files[0]) == False or os.path.isfile(args.in_files[1]) == False:
        print("File does not exist")
        print("Exiting...")
        sys.exit()

    # Ensuring two threads are always run.
    args.threads = 2

    ###
    # Running the custom model interface script.
    model_info = custom_model(username = args.credentials[0],password = args.credentials[1])
    if model_info != None:
        args.lm_custom_id = model_info
    ###

    # Adding audio files to analysis queue.
    q = Queue.Queue()
    fileNumber = 0
    print("Files to analyze...")
    for filename,name in map(None,lines,args.Names):
    	print(filename + " -> Speaker Name: " + name)
    	q.put((fileNumber,filename))
    	fileNumber += 1
    print("\n")

    hostname = "stream.watsonplatform.net"
    headers = {'X-WDC-PL-OPT-OUT': '1'} if args.optOut else {}

    # Authentication Header
    if args.tokenauth:
        headers['X-Watson-Authorization-Token'] = (
            Utils.getAuthenticationToken('https://' + hostname,
                                         'speech-to-text',
                                         args.credentials[0],
                                         args.credentials[1]))
    else:
        auth = args.credentials[0] + ":" + args.credentials[1]
        headers["Authorization"] = "Basic " + base64.b64encode(auth)

    print(headers)


    # Create a WS Server factory with our protocol
    fmt = "wss://{}/speech-to-text/api/v1/recognize?model={}"
    url = fmt.format(hostname, args.model)
    if args.am_custom_id != None:
    	url += "&acoustic_customization_id=" + args.am_custom_id
    if args.lm_custom_id != None:
        url += "&customization_id=" + args.lm_custom_id
        # ADD ADDITIONAL ARGUMENTS TO THE STT SERVICE HERE!!!!
        # Additional arguments might include:
        # 1.    Customization weight
        url += "&customization_weight=0.3"    # Customization model weightage
        url += "&profanity_filter=False"      # Turning off the profanity filter. (Kids Beware!)

    summary = {}
    factory = WSInterfaceFactory(q, summary, args.dirOutput, args.contentType,
                                 args.model, url, headers, debug=False)
    factory.protocol = WSInterfaceFactory

    for i in range(min(int(args.threads), q.qsize())):
    	factory.prepareUtterance()

        # SSL client context: default
        if factory.isSecure:
            contextFactory = ssl.ClientContextFactory()
        else:
            contextFactory = None
        connectWS(factory, contextFactory)


    reactor.run()

    # Sorting speaker names in alphabetical order
    # This is to ensure correct name is attributed to
    # the correct speaker at the CSV build stage.
    speaker_names = []
    speaker_names.append(args.Names[0])
    speaker_names.append(args.Names[1])
    speaker_names.sort()

    # Building and writing the seperate csv files
    seperate_output = build_seperate_CSV(json1 = JSON1,json2 = JSON2,name1 = speaker_names[0],name2 = speaker_names[1])
    if len(seperate_output[0]) > 0:
        seperate_output[0] = seperate_postprocessing(seperate_output[0])
    if len(seperate_output[1]) > 0:
        seperate_output[1] = seperate_postprocessing(seperate_output[1])
    writeCSV(seperate_output[0],'seperate-1.csv')
    writeCSV(seperate_output[1],'seperate-2.csv')

    # Combining and doing postprocessing on the two individual speaker files.
    combined_output = combined_postprocessing(seperate_output[0],seperate_output[1])
    writeCSV(combined_output,'both-speakers.csv')
    audio = args.combined_audio[0]
    audio = audio[2:audio.find('.wav')]
    build_CHAT(combined_output,args.Names[0],args.Names[1],audio)


    # Creating and indenting the CA files.
    os.system('./converter chat2calite combined.cha')
    os.system('./indent combined.S.ca')
    os.remove('combined.S.ca')
    os.rename('combined.S.indnt.cex','combined.S.ca')
























