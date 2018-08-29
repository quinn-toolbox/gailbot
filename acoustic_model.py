'''
	Script dealing with listing, deleting, and 
	creating custom acoustic models associated with 
	a particulat  Watson instance.
	Called from a seperate driver file.
'''


import requests
import json
import codecs
import sys, time
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from pydub import AudioSegment
from pydub.utils import make_chunks


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

headers = {'Content-Type' : "application/json"}

# Function providing the user-API interface.
def custom_model_acoustic(username,password):
	option = raw_input('\nPress 1 to use default acoustic model\nPress 2 to for custom acoustic model option\n')
	if option == '1':
		return None
	while True:
		option2 = raw_input("Press 1 to select custom acoustic model\nPress 2 to delete custom acoustic model\nPress 3 to create new acoustic model\nPress 4 for default acoustic model\n")
		if option2 == '1':
			get_model_list(username,password)
			customID = raw_input("Enter custom acoustic model ID from above list (Excluding punctuation marks!)\nPress 0 to go back to options\n")
			if customID != '0':
				return customID
			local_option = raw_input("Press 'Y' to exit\nPress 'N' to repeat options\n")
			if local_option == 'Y' or local_option == 'y':
				break
		elif option2 == '2':
			get_model_list(username,password)
			customID = raw_input("Enter custom ID of acoustic model to delete\nPress 0 to go back to options\n")
			if customID != '0':
				delete_model(username,password,customID)
			local_option = raw_input("Press 'Y' to exit\nPress 'N' to repeat options\n")
			if local_option == 'Y' or local_option == 'y':
				break
		elif option2 == '3':
			update = None
			name = raw_input("Enter new acoustic model name\n")
			description = raw_input("Enter new acoustic model description\n")
			custom_ID = create_model(username = username, password = password, name = name, description = description)
			while True:
				option = raw_input("Press 1 to add single audio file\n")
				if option == '1':
					filename = raw_input("Enter audio-file name\n")
					add_audio(username,password,filename,custom_ID)
					train_model(username,password,custom_ID)
					break
				else:
					print('Incorrect option. Try again\n')

			get_model_list(username,password)
			local_option = raw_input("Press 'Y' to exit\nPress 'N' to repeat options\n")
			if local_option == 'Y' or local_option == 'y':
				break
		elif option2 == '4':
			return None
		else:
			print('Incorrect option. Try again\n')


# Function that adds audio to the acoustic model
def add_audio(username,password,filename,customID):

	custom_headers = {'Content-Type': "audio/wav"}

	if len(AudioSegment.from_file(filename)) <= 600000:
		print('Error: The audio file must be at least 10 minutes long')
		sys.exit(-1)
	if check_extension(filename,'wav') == False:
		print("Error: Wav audio file expected")
		sys.exit(-1)
	print('\nAdding audio file...')
	name = filename[:filename.rfind('.')]
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/acoustic_customizations/{0}/audio/{0}".format(customID,name)
	with open(filename, 'rb') as f:
		r = requests.post(uri, auth=(username,password), verify=False, headers=custom_headers, data=f)

	print "Adding audio file returns: ", r.status_code
	if r.status_code != 201:
	   print "Failed to add audio file"
	   print r.text
	   sys.exit(-1)

	print('Checking status of audio analysis...')
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/acoustic_customizations/{0}/audio/{0}".format(customID,name)
	r = requests.get(uri, auth=(username,password), verify=False, headers=custom_headers)
	respJson = r.json()
	status = respJson['status']
	time_to_run = 10
	while (status != 'ok'):
	    time.sleep(10)
	    r = requests.get(uri, auth=(username,password), verify=False, headers=custom_headers)
	    respJson = r.json()
	    if respJson['status'] == 'invalid':
	    	print('Error: Audio file size exceeds 100 MB')
	    	sys.exit(-1)
	    status = respJson['status']
	    print "status: ", status, "(", time_to_run, ")"
	    time_to_run += 10

	print "Audio analysis done!"

# Function that trains the acoustic model with the added audio file
def train_model(username,password,customID):
	print('\nTraining custom acoustic model')
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/acoustic_customizations/{0}/train".format(customID)
	data = {}
	jsonObject = json.dumps(data).encode('utf-8')
	r = requests.post(uri, auth=(username,password), verify=False, data=jsonObject)

	print "Training request returns: ", r.status_code
	if r.status_code != 200:
	   print "Training failed to start - exiting!"
	   sys.exit(-1)

	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/acoustic_customizations/{0}".format(customID)
	r = requests.get(uri, auth=(username,password), verify=False, headers=headers)
	respJson = r.json()
	status = respJson['status']
	time_to_run = 10
	while (status != 'available'):
	    time.sleep(10)
	    r = requests.get(uri, auth=(username,password), verify=False, headers=headers)
	    respJson = r.json()
	    status = respJson['status']
	    print "status: ", status, "(", time_to_run, ")"
	    time_to_run += 10

	print "Training complete!"



# Function that creates a new model
def create_model(username,password, description,name):
	print "\nCreating custom acoustic model..."
	data = {"name" : name, "base_model_name" : "en-US_BroadbandModel", "description" : description}
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/acoustic_customizations"
	jsonObject = json.dumps(data).encode('utf-8')
	resp = requests.post(uri, auth=(username,password), verify=False, headers=headers, data=jsonObject)

	print "Acoustic Model creation returns: ", resp.status_code
	if resp.status_code != 201:
	   print "Failed to create acoustic model"
	   print resp.text
	   sys.exit(-1)

	respJson = resp.json()
	customID = respJson['customization_id']
	print "Acoustic Model customization_id: ", customID
	return customID



# Function that returns a list of all the available models
def get_model_list(username,password):
	print "\nGetting custom acoustic models..."
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/acoustic_customizations"
	r = requests.get(uri, auth=(username,password), verify=False, headers=headers)
	print "Get models returns: ", r.status_code
	print r.text


# Function that deletes the model corresponding to
# the given model ID.
def delete_model(username,password,customID):
	print "\nDeleting custom acoustic model..."
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/acoustic_customizations/"+customID
	r = requests.delete(uri, auth=(username,password), verify=False, headers=headers)
	respJson = r.json()



# Function that checks the file extension
def check_extension(filename,extension):
	if filename[filename.rfind('.')+1:] == extension:
		return True
	else:
		return False