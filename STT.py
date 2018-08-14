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
from acoustic_model import custom_model_acoustic 		# Required for acoustic custom model interface.
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

    def setUtterance(self, utt):

        self.uttNumber = utt[0]
        self.uttFilename = utt[1]
        self.summary[self.uttNumber] = {"hypothesis": "",
                                        "status": {"code": "", "reason": ""}}
        self.fileJson = "{}/{}.json.txt".format(self.dirOutput, self.uttNumber)
        try:
            os.remove(self.fileJson)
        except OSError:
            pass


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
                "interim_results": True,
                "inactivity_timeout": 600,
                'max_alternatives': 3,
                'timestamps': True,
                'word_confidence': True,
                'profanity_filter' : False,
                'speaker_labels': True}


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

        with open(self.fileJson, "a") as f:
            f.write(json.dumps(self.json_output, indent=4,
                sort_keys=True))

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
    		help='Path to audio file', nargs = "*", required = True )
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
    if len(args.in_files) == 2: 
        if os.path.isfile(args.in_files[0]) == False or os.path.isfile(args.in_files[1]) == False:
            print("File does not exist")
            print("Exiting...")
            sys.exit(-1)
    else:
        if os.path.isfile(args.in_files[0]) == False:
            print("File does not exist")
            print("Exiting...")
            sys.exit(-1)

    # Changing threads based on the number of files
    if len(args.in_files) == 1:
        args.threads = 1
    elif len(args.in_files) == 2:
        args.thread = 2
    else:
        print("Invalid file argument")
        print("Exiting...")
        sys.exit(-1)

    # Chaning the name argument if there is only one audio file
    if len(args.in_files) == 1:
        args.Names = ['Speaker'] 

    ###
    # Running the custom model interface script.
    model_info = custom_model(username = args.credentials[0],password = args.credentials[1])
    if model_info != None:
        args.lm_custom_id = model_info
    ###

    ###
    # Running the acoustic custom model interface script
    acoustic_info = custom_model_acoustic(username = args.credentials[0],password = args.credentials[1])
    if acoustic_info != None:
    	args.am_custom_id = acoustic_info
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





















