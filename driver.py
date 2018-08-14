'''
	Script that recieves different inputs from user,
	determines the type of input, performs file verification,
	generates new-file names and calls the STT script, the 
	customization interface script and the post-processing 
	script.
'''

import os.path
import argparse                   
import sys
import os
from pydub import AudioSegment
from pydub.utils import make_chunks
import json
import csv
import post_processing
from operator import itemgetter


# Constant for the audio file length
CHUNK_SPLIT_MS = 600000
CHUNK_SPLIT_BYTES = 800000000

# Function that verifies that the given file exists.
def file_exists(filename):
	if os.path.is_file(filename) == True:
		return True
	else:
		return False

# Function that verifies user input based on the option
def verify_input(option,files,names):
	if option == '2' or option == '1':
		if len(files) != 2:
			print('Error: Two MXF files expected')
			return False
		if check_extension(files[0],"MXF") == False or check_extension(files[1],"MXF") == False:
			print("Error: Verify MXF extesnsion")
			return False
		if len(names) != 2:
			print("Error: Two names expected")
			return False
		return True
	elif option == '4':
		if len(files) != 1:
			print("Error: One MXF file expected")
			return False
		if check_extension(files[0],"MXF") == False:
			print("Error: Verify MXF extesnsion")
			return False
		if len(names) != 2:
			print("Error: Two names expected")
			return False
		return True
	elif option == '3':
		if len(files) != 2:
			print("Error: Two wav files expected")
			return False
		if check_extension(files[0],'wav') == False or check_extension(files[1],'wav')==False:
			print("Error: Verify wav extension")
			return False
		if len(names) != 2:
			print("Error: Two names expected")
			return False
		return True
	elif option == '5':
		if len(files) != 1:
			print("Error: One wav files expected")
			return False
		if check_extension(files[0],'wav') == False:
			print("Error: Verify wav extension")
			return False
		if len(names) != 2:
			print("Error: Two names expected")
			return False
		return True




# Function that gets the type input from the user.
def get_type_input():
	print('\n')
	print('Welcome to Gailbot 2.0!\n')
	print('Press 1 to transcribe one or two MXF files, with a separate channel for each speaker')
	print('Press 2 to transcribe two MXF files part of the same conversation, getting audio from each file separately')
	print('Press 3 to transcribe two wav files corresponding to different speakers in one conversation')
	print('Press 4 to transcribe a single MXF file with a single channel with using dialogue model')
	print('Press 5 to transcribe a single wav using the dialogue model')
	while True:
		option = raw_input('Please enter your  option\n')
		if option < 0 and option > 5:
			print('Incorrect option. Please try again')
		else:
			break
	return option

# Function that spilts the audio file into multiple
# smaller parts
def chunk_audio(filename,count):
	myaudio = AudioSegment.from_file(filename,'wav')
	print('\n')
	chunk_length_ms = CHUNK_SPLIT_MS
	# Making 8 minute audio chunks.
	total = 0
	curr_name = filename[:filename.rfind('.')]
	chunks = make_chunks(myaudio, chunk_length_ms)
	for i, chunk in enumerate(chunks):
	    chunk_name = "-chunk{0}.wav".format(i)
	    chunk_name = curr_name + chunk_name
	    print "exporting", chunk_name
	    chunk.export(chunk_name, format="wav")
	    total+=1
	print('\n')
	return total




# Funcntion sendign different calls to Watson.
def send_call(credentials,filenames,speaker_names, option,num_files,new_name):
	if option == '1' or option == '2':
		command = "python STT.py -credentials "+credentials[0]+":"+credentials[1]+" -model en-US_BroadbandModel"\
					" -files "+file1+" "+file2+ " -names "+speaker_names[0]+" "+speaker_names[1]+" -audio "+new_name
		os.system(command)
	elif option == '3' and num_files == 2:
		command = "python STT.py -credentials "+credentials[0]+":"+credentials[1]+" -model en-US_BroadbandModel"\
					" -files "+filenames[0]+" "+filenames[1]+ " -names "+speaker_names[0]+" "+speaker_names[1]+" -audio "+new_name

		os.system(command)
	elif option == '4' and num_files == 1:
		command = "python STT.py -credentials "+credentials[0]+":"+credentials[1]+" -model en-US_BroadbandModel"\
					" -files "+filenames[0]+ " -names "+speaker_names[0]+" "+speaker_names[1]+" -audio "+filenames[0]
		os.system(command)
	elif option == '5' and num_files == 1:
		command = "python STT.py -credentials "+credentials[0]+":"+credentials[1]+" -model en-US_BroadbandModel"\
					" -files "+filenames[0]+ " -names "+speaker_names[0]+" "+speaker_names[1]+" -audio "+filenames[0]
		os.system(command)




# function to check the credentials format
def check_credentials(credentials):
    elements = credentials.split(":")
    if len(elements) == 2:
        return elements
    else:
        raise argparse.ArgumentTypeError(
            '"%s" is not a valid format for the credentials ' % credentials)


# function to check that a value is a positive integer
def check_positive_int(value):
    ivalue = int(value)
    if ivalue < 1:
        raise argparse.ArgumentTypeError(
            '"%s" is an invalid positive int value' % value)
    return ivalue


# Function to verify the given files
def verify_files(all_files):
	for file in all_files:
		if os.path.isfile(file) == False:
			return False
	return True

# Function that extracts audio from video files
def extract_audio(in_files):
	if check_extension(in_files,"MXF") == True:
		new_path = in_files[:in_files.rfind('.')]
		command = "ffmpeg -i "+in_files+" -map 0:1 -c copy -acodec pcm_s16le -ar 16000 "+ new_path +"-speaker1.wav -map 0:2 -c copy -acodec pcm_s16le -ar 16000 "+ new_path +"-speaker2.wav"
		os.system(command)
		return new_path

# Function that extracts audio from a single channel file
def extract_audio_single(in_files):
	if check_extension(in_files,"MXF") == True:
		new_path = in_files[:in_files.rfind('.')]
		command = "ffmpeg -i "+in_files+" -acodec pcm_s16le -ar 16000 "+new_path+"-speaker.wav"
		os.system(command)
		return new_path



# Fucntion that overlays the audio
def overlay(file1,file2):
	if check_extension(file1,'wav') == True and check_extension(file2,'wav') == True:
		if file1.find('/') != -1:
			audio1 = file1[file1.rfind('/')+1:file1.rfind('.')]
		else:
			audio1 = file1[:file1.rfind('.')]
		if file1.find('/') != -1:
			audio2 = file2[file2.rfind('/')+1:file1.rfind('.')]
		else:
			audio2 = file2[:file2.rfind('.')]
		new_name = audio1+"-"+audio2+'-combined.wav'
		audio1 = audio1 +'.wav'
		audio2 = audio2 +'.wav'

		command = "ffmpeg -i "+audio1+" -i "+audio2+ " -filter_complex amix=inputs=2:duration=longest:dropout_transition=3 "+new_name
		os.system(command)
		return new_name




# Function that checks the file extension
def check_extension(filename,extension):
	if filename[filename.rfind('.')+1:] == extension:
		return True
	else:
		return False

# Function that builds a CSV file for a single audio file
def build_single_CSV(json1,name1,name2):
	new_json = []
	times = []
	for item in json1:
		if item['results'][0]['final'] == True:
	  		new_json.append(item)
	  	elif 'speaker_labels' in item:
	  		times.append(item['speaker_labels'])


	all_lines = []

	data1 = []
	for item in new_json:
		sub_item = item['results'][0]['alternatives'][0]['timestamps']
		for subdata in sub_item:
	  		data1.append(subdata)

	for res1 in data1:
		trans1 = " "+res1[0]+" "
		start1 = res1[1]
		end1 = res1[2]
		all_lines.append(['speaker',start1,end1,trans1])

	time_data = []
	for time in times:
		for individual in time:
			name = individual['speaker']
			start = individual['from']
			end = individual['to']
			confidence = individual['confidence']
			time_data.append([name,start,end,confidence])

	all_lines = sorted(all_lines, key = itemgetter(1))
	time_data = sorted(time_data,key = itemgetter(1))

	count = 0
	new_time_data = []
	while count < len(time_data):
		curr = time_data[count]
		conf = curr[-1]
		pos = count
		while time_data[pos][1] == curr[1]:
			if round(float(time_data[pos][-1]),2) > round(float(curr[-1]),2):
				curr = time_data[pos]
			pos+=1
			if pos >= len(time_data):
				break
		count = pos-1
		new_time_data.append(curr)
		count+=1

	new_all_lines = []
	count = 0
	while count < len(all_lines):
		curr = all_lines[count]
		curr_start = all_lines[count][1]
		pos = count
		while all_lines[pos][1] == all_lines[count][1]:
			pos+=1
			if pos >= len(all_lines):
				break
		count = pos-1
		new_all_lines.append(curr)
		count+=1


	for lines,time in map(None,new_all_lines,new_time_data):
		if lines != None and time != None:
			if lines[1] == time[1] and lines[2] == time[2]:
				if time[0] == 0:
					lines[0] = 'SP1'
				elif time[0] == 1:
					lines[0] = 'SP2'
				else:
					lines[0] = 'SP1'
		else:
			lines[0] = 'SP1'



	return new_all_lines




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


# Function that concatenates the csv files for chunks
def concat_csv(num_chunks):
	time_diff_ms = CHUNK_SPLIT_MS/1000
	speaker_1_list = []
	speaker_2_list = []
	for i in range(num_chunks):
		name1 = 'separate-1-{0}.csv'.format(i)
		name2 = 'separate-2-{0}.csv'.format(i)
		with open(name1, 'rb') as f:
			reader = csv.reader(f)
			data = list(reader)
			for item in data:
				item[1] = round(float(item[1])+(time_diff_ms*i),2)
				item[2] = round(float(item[2])+(time_diff_ms*i),2)
				item[1] = str(item[1])
				item[2] = str(item[2])
				speaker_1_list.append(item)
		with open(name2,'rb') as f:
			reader = csv.reader(f)
			data = list(reader)
			for item in data:
				item[1] = round(float(item[1])+(time_diff_ms*i),2)
				item[2] = round(float(item[2])+(time_diff_ms*i),2)
				item[1] = str(item[1])
				item[2] = str(item[2])
				speaker_2_list.append(item)
		os.remove(name1)
		os.remove(name2)
	writeCSV(speaker_1_list,'speaker-1.csv')
	writeCSV(speaker_2_list,'speaker-2.csv')

# Function that concatenates the csv file for 
# a single speaker.
def concat_csv_single(num_chunks):
	time_diff_ms = CHUNK_SPLIT_MS/1000
	speaker_1_list = []
	for i in range(num_chunks):
		name1 = 'separate-1-{0}.csv'.format(i)
		with open(name1, 'rb') as f:
			reader = csv.reader(f)
			data = list(reader)
			for item in data:
				item[1] = round(float(item[1])+(time_diff_ms*i),2)
				item[2] = round(float(item[2])+(time_diff_ms*i),2)
				item[1] = str(item[1])
				item[2] = str(item[2])
				speaker_1_list.append(item)
		os.remove(name1)
	writeCSV(speaker_1_list,'separate-1.csv')

if __name__ == '__main__':

	# parse command line parameters
	parser = argparse.ArgumentParser(
		description = ('client to recoginize type of request to be set to te Watson STT system'))
	parser.add_argument(
		'-credentials', action = 'store', dest = 'credentials', 
		help = "Basic Authentication credentials in the form 'username:password", required = True)
	parser.add_argument(
		'-files', action = 'store', dest = 'in_files', default = None,
		help = 'path to the audio/video file(s)', nargs = '*', required = True)
	parser.add_argument(
		'-names', action = 'store', dest = 'Names', default = None,
		help = 'Speaker names', nargs = 2, required = True)

	args = parser.parse_args()


	trans_type = get_type_input()
	input_check = verify_input(trans_type,args.in_files,args.Names)
	if input_check == False:
		print("Exiting... ")
		sys.exit(-1)
	check = verify_files(args.in_files)
	if check == False:
		print('One of the given files does not exist')
		print('Exiting...')
		sys.exit(-1)

	# Sorting speaker names in alphabetical order
    # This is to ensure correct name is attributed to
    # the correct speaker at the CSV build stage.
	speaker_names = []
	speaker_names.append(args.Names[0])
	speaker_names.append(args.Names[1])
	speaker_names.sort()


	args.credentials = [args.credentials[:args.credentials.rfind(':')] ,args.credentials[args.credentials.rfind(":")+1:]]

	# Getting audio from MXF files
	MXF = True
	for file in args.in_files:
		MXF = check_extension(file,"MXF")
		if MXF == False:
			break
	if MXF ==  True:
		if trans_type == '1':
			new_path = extract_audio(args.in_files[0])
			file1 = new_path+'-speaker1.wav'
			file2 = new_path+"-speaker2.wav"
			args.in_files = [file1, file2]
		elif trans_type == '4':
			new_path = extract_audio_single(args.in_files[0])
			path = new_path+'-speaker.wav'
			args.in_files = [path]
		elif trans_type == '2':
			new_path = extract_audio_single(args.in_files[0])
			file1 = new_path+'-speaker.wav'
			new_path = extract_audio_single(args.in_files[1])
			file2 = new_path+"-speaker.wav"
			args.in_files = [file1, file2]


	# Chunking audio files larger than 50 minutes.
	chunk = False
	count = 0
	num_chunks = []
	print('Analyzing file size. Please wait...')
	for file in args.in_files:
		#if len(AudioSegment.from_file(file)) > CHUNK_SPLIT_MS:
		if os.path.getsize(file) > CHUNK_SPLIT_BYTES:
			print('\nFile-size exceeds limit. Chunking audio...')
			chunk = True
			total_chunks = chunk_audio(file,count)
			num_chunks.append(total_chunks)
		count+=1

	if chunk == True and trans_type != 4 and trans_type != 5:
		if len(args.in_files) == 2: 
			if num_chunks[0] != num_chunks[1]:
				print("ERROR: Number of chunks do not match")
				print('Exiting...')
				sys.exit(-1)

			new_name = overlay(args.in_files[0],args.in_files[1])
			orig1 = args.in_files[0]
			orig2 = args.in_files[1]
			# Sending in the file if they were chunked.
			for i in range(num_chunks[0]):
				file1name = ""
				file2name = ""
				file1name = "-chunk{0}.wav".format(i)
				file1name = orig1[:orig1.rfind('.')]+file1name
				file2name = "-chunk{0}.wav".format(i)
				file2name = orig2[:orig2.rfind('.')]+file2name
				args.in_files = []
				args.in_files = [file1name, file2name] 
				if os.path.exists('0.json.txt'):
					os.remove('0.json.txt')
				if os.path.exists('1.json.txt'):
					os.remove('1.json.txt')
				send_call(args.credentials,args.in_files,args.Names,trans_type,2,new_name)	
				# Building the individual speaker CSV files.
				with open('0.json.txt') as speaker1_data:
					speaker1_result  = json.load(speaker1_data)
				with open('1.json.txt') as speaker2_data:
					speaker2_result = json.load(speaker2_data)	
				seperate_output = build_seperate_CSV(speaker1_result,speaker2_result,args.Names[0],args.Names[1])
				writeCSV(seperate_output[0],'separate-1-{0}.csv'.format(i))
				writeCSV(seperate_output[1],'separate-2-{0}.csv'.format(i))
				if os.path.exists('0.json.txt'):
					os.remove('0.json.txt')
				if os.path.exists('1.json.txt'):
					os.remove('1.json.txt')
				os.remove(file1name)
				os.remove(file2name)	
			# Combining all the seperate csv files
			concat_csv(num_chunks[0])


		elif len(args.in_files) == 1:
			orig1 = args.in_files[0]
			for i in range(num_chunks[0]):
				file1name = ''
				file1name = "-chunk{0}.wav".format(i)
				file1name = orig1[:orig1.rfind('.')]+file1name
				args.in_files = []
				args.in_files = [file1name] 
				if os.path.exists('0.json.txt'):
					os.remove('0.json.txt')
				send_call(args.credentials,args.in_files,args.Names,trans_type,1,'')
				#** Write a function here to build a separate CSV file with speaker labels.
				with open('0.json.txt') as speaker1_data:
					speaker1_result  = json.load(speaker1_data)
				output = build_single_CSV(speaker1_result,args.Names[0],args.Names[1])
				writeCSV(output,'separate-1-{0}.csv'.format(i))
				if os.path.exists('0.json.txt'):
					os.remove('0.json.txt')
				os.remove(file1name)
			concat_csv_single(num_chunks[0])
			args.in_files[0] = orig1

	elif (trans_type == '1' or trans_type == '2' or trans_type == '3') and len(args.in_files) == 2:
		if os.path.exists('0.json.txt'):
			os.remove('0.json.txt')
		if os.path.exists('1.json.txt'):
			os.remove('1.json.txt')	
		new_name = overlay(args.in_files[0],args.in_files[1])
		new_name = new_name[:new_name.rfind('.')]
		send_call(args.credentials,args.in_files,args.Names,trans_type,len(args.in_files),new_name)

		# Building the individual speaker CSV files.
		with open('0.json.txt') as speaker1_data:
			speaker1_result  = json.load(speaker1_data)
		with open('1.json.txt') as speaker2_data:
			speaker2_result = json.load(speaker2_data)	
		seperate_output = build_seperate_CSV(speaker1_result,speaker2_result,args.Names[0],args.Names[1])
		writeCSV(seperate_output[0],'separate-1.csv')
		writeCSV(seperate_output[1],'separate-2.csv')
		if os.path.exists('0.json.txt'):
			os.remove('0.json.txt')
		if os.path.exists('1.json.txt'):
			os.remove('1.json.txt')

	elif (trans_type == '4' or trans_type == '5') and len(args.in_files) == 1:
		if os.path.exists('0.json.txt'):
			os.remove('0.json.txt')
		send_call(args.credentials,args.in_files,args.Names,trans_type,len(args.in_files),'')

		#** Write a function here to build a separate CSV file with speaker labels.
		# Complete the build single CSV function
		with open('0.json.txt') as speaker1_data:
			speaker1_result  = json.load(speaker1_data)
		output = build_single_CSV(speaker1_result,args.Names[0],args.Names[1])
		writeCSV(output,'separate-1.csv') 
		if os.path.exists('0.json.txt'):
			os.remove('0.json.txt')


	# Applying post_processing functions to the data
	if len(args.in_files) > 1:
		all_data = post_processing.read_data_double('separate-1.csv','separate-2.csv')
		if len(all_data[0]) > 0 and len(all_data[1]) > 0:
			all_data[0] = post_processing.seperate_postprocessing(all_data[0])
			all_data[1] = post_processing.seperate_postprocessing(all_data[1])
			os.remove('separate-1.csv')
			os.remove('separate-2.csv')
			writeCSV(all_data[0],'speaker-1.csv')
			writeCSV(all_data[1],'speaker-2.csv')

		# Combining and doing postprocessing on the two individual speaker files.
		combined_output = post_processing.combined_postprocessing(all_data[0],all_data[1])
		writeCSV(combined_output,'combined.csv')
		post_processing.build_CHAT(combined_output,args.Names[0],args.Names[1],new_name)

	elif len(args.in_files) == 1:
		all_data = post_processing.read_data_single('separate-1.csv')
		all_data = post_processing.seperate_postprocessing(all_data)
		os.remove('separate-1.csv')
		writeCSV(all_data,'separate-1.csv')
		combined_output = post_processing.combined_post_processing_single(all_data)
		writeCSV(combined_output,'combined.csv')
		new_name = args.in_files[0]
		post_processing.build_CHAT(combined_output,'SP1','SP2',new_name[:new_name.rfind('.')])
		os.remove('separate-1.csv')

	# Creating and indenting the CA files.
	os.system('./converter chat2calite combined.cha')
	os.system('./indent combined.S.ca')
	os.remove('combined.S.ca')
	os.rename('combined.S.indnt.cex','combined.S.ca')























