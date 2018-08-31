'''
	Script dealing with listing, deleting, and 
	creating custom models associated with a 
	particular Watson instance.
	Called from a seperate driver file.
	Currently being exported to STT.py
'''

import requests
import json
import codecs
import sys, time
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

headers = {'Content-Type' : "application/json"}

# Function providing user-API interface
def custom_model(username, password):
	out = {"base": "en-US_BroadbandModel", "cust" : None}
	option = raw_input("Press 1 for default language model (en-US_BroadbandModel)\nPress 2 for custom language model options\n")
	if option == '1':
		return out
	while True:
		option2 = raw_input("Press 1 to select custom model\nPress 2 to delete custom model\nPress 3 to create new model\nPress 4 for default model\nPress 5 to list available API models\nPress 6 for information on a specific base model (Name required)\n")
		if option2 == '1':
			get_model_list(username,password)
			print("NOTE: The custom language model's base model must be the same as the selected base model")
			customID = raw_input("Enter custom model ID from above list (Excluding punctuation marks!)\nPress 0 to go back to options\n")
			if customID != '0':
				out["cust"] = customID
				return out
			local_option = raw_input("Press 'Y' to exit\nPress 'N' to repeat options\n")
			if local_option == 'Y' or local_option == 'y':
				break
		elif option2 == '2':
			get_model_list(username,password)
			customID = raw_input("Enter custom ID of model to delete\nPress 0 to go back to options\n")
			if customID != '0':
				delete_model(username,password,customID)
			local_option = raw_input("Press 'Y' to exit\nPress 'N' to repeat options\n")
			if local_option == 'Y' or local_option == 'y':
				break
		elif option2 == '3':
			update = None
			name = raw_input("Enter new model name\n")
			description = raw_input("Enter new model description\n")
			custom_ID = create_model(username = username, password = password, name = name, description = description)
			
			while True:
				option = raw_input("Press 1 to add file corpus\nPress 2 to add single word\nPress 3 to add multiple words\n")
				if option == '1':
					filename = raw_input("Enter corpus filename\n")
					add_corpus(username,password,filename,custom_ID)
					train_model(username,password,custom_ID)
					break
				elif option == '2':
					word = raw_input("Enter word\n")
					sounds_like = raw_input("What does the word sound like?\n")
					display_as = raw_input("How should the word be displayed?\n")
					add_word(username,password,word,sounds_like,display_as,custom_ID)
					train_model(username,password,custom_ID)
					break
				elif option == '3':
					final = []
					while True:
						data = {"word":"","sounds_like":[],"display_as":""}
						word = raw_input("Enter word\n")
						sounds_like = raw_input("What does the word sound like?\n")
						display_as = raw_input("How should the word be displayed?\n")
						option_local = raw_input("Press 1 to add more words. 2 to end\n")
						data['word'] = word
						data['sounds_like'].append(sounds_like)
						data['display_as'] = display_as
						final.append(data)
						if option_local == '2':
							break
					add_multiple_words(username,password,final,custom_ID)
					train_model(username,password,custom_ID)
					break
				else:
					print('Incorrect option. Try again\n')

			get_model_list(username,password)
			local_option = raw_input("Press 'Y' to exit\nPress 'N' to repeat options\n")
			if local_option == 'Y' or local_option == 'y':
				break
		elif option2 == '4':
			return out
		elif option2 == '5':
			list_models(username,password)
			print("To use any of the base models, use option 1 and enter model name\n")
			name = raw_input("Enter model name\n")
			out["base"] = name
			return out
		elif option2 == '6':
			modelinfo = raw_input("Enter the name of the base model\n")
			get_basemodel_info(username,password,modelinfo)
		else:
			print('Incorrect option. Try again\n')

# Function that returns a list of all available custom models
def get_model_list(username,password):
	print "\nGetting custom models..."
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/customizations"
	r = requests.get(uri, auth=(username,password), verify=False, headers=headers)
	print "Get models returns: ", r.status_code
	print r.text

# Function that deletes the model corresponding to
# the given model ID.
def delete_model(username,password,customID):
	print "\nDeleting custom model..."
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/customizations/"+customID
	r = requests.delete(uri, auth=(username,password), verify=False, headers=headers)
	respJson = r.json()

# Function that creates a new model
def create_model(username,password, description,name):
	print "\nCreating custom model..."
	data = {"name" : name, "base_model_name" : "en-US_BroadbandModel", "description" : description}
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/customizations"
	jsonObject = json.dumps(data).encode('utf-8')
	resp = requests.post(uri, auth=(username,password), verify=False, headers=headers, data=jsonObject)

	print "Model creation returns: ", resp.status_code
	if resp.status_code != 201:
	   print "Failed to create model"
	   print resp.text
	   sys.exit(-1)

	respJson = resp.json()
	customID = respJson['customization_id']
	print "Model customization_id: ", customID
	return customID

# Function that sends a corpus to the server to be analyzed 
# into the new custom model.
def add_corpus(username, password, filename,customID):
	corpus_file = filename
	corpus_name = filename[:filename.rfind(".")]

	print "\nAdding corpus file..."
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/customizations/"+customID+"/corpora/"+corpus_name
	with open(corpus_file, 'rb') as f:
	   r = requests.post(uri, auth=(username,password), verify=False, headers=headers, data=f)

	print "Adding corpus file returns: ", r.status_code
	if r.status_code != 201:
	   print "Failed to add corpus file"
	   print r.text
	   sys.exit(-1)


	print "Checking status of corpus analysis..."
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/customizations/"+customID+"/corpora/"+corpus_name
	r = requests.get(uri, auth=(username,password), verify=False, headers=headers)
	respJson = r.json()
	status = respJson['status']
	time_to_run = 10
	while (status != 'analyzed'):
	    time.sleep(10)
	    r = requests.get(uri, auth=(username,password), verify=False, headers=headers)
	    respJson = r.json()
	    status = respJson['status']
	    print "status: ", status, "(", time_to_run, ")"
	    time_to_run += 10

	print "Corpus analysis done!"

# Function that adds a single word to the model
def add_word(username,password,word,sounds_like,display_as,customID):
	print "\nAdding single word..."
	data = {"sounds_like" : [sounds_like], "display_as" : display_as}
	wordToAdd = word
	u = unicode(wordToAdd, "utf-8")
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/customizations/"+customID+"/words/"+u
	jsonObject = json.dumps(data).encode('utf-8')
	r = requests.put(uri, auth=(username,password), verify=False, headers=headers, data=jsonObject)

	print "Adding single word returns: ", r.status_code
	print "Single word added!"

# Function that adds multiple words to a model to be analyzed
def add_multiple_words(username,password,interim_data,customID):
	print "\nAdding multiple words..."
	print interim_data
	data = {"words": interim_data}
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/customizations/"+customID+"/words"
	jsonObject = json.dumps(data).encode('utf-8')
	r = requests.post(uri, auth=(username,password), verify=False, headers=headers, data=jsonObject)

	print "Adding multiple words returns: ", r.status_code

	##########################################################################
	# Get status of model - only continue to training if 'ready'
	##########################################################################
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/customizations/"+customID
	r = requests.get(uri, auth=(username,password), verify=False, headers=headers)
	respJson = r.json()
	status = respJson['status']
	print "Checking status of model for multiple words..."
	time_to_run = 10
	while (status != 'ready'):
	    time.sleep(10)
	    r = requests.get(uri, auth=(username,password), verify=False, headers=headers)
	    respJson = r.json()
	    status = respJson['status']
	    print "status: ", status, "(", time_to_run, ")"
	    time_to_run += 10

	print "Multiple words added!"

# Function that trains the model with the input data provided.
def train_model(username,password,customID):


	print "\nTraining custom model..."
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/customizations/"+customID+"/train"
	data = {}
	jsonObject = json.dumps(data).encode('utf-8')
	r = requests.post(uri, auth=(username,password), verify=False, data=jsonObject)

	print "Training request returns: ", r.status_code
	if r.status_code != 200:
	   print "Training failed to start - exiting!"
	   sys.exit(-1)

	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/customizations/"+customID
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

# Function that lists all the base models available 
# within the API.
def list_models(username,password):
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/models"
	r = requests.get(uri, auth=(username,password), verify=False, headers=headers)
	respJson = r.json()
	print "List models returns: ", r.status_code
	print r.text

# Function that gets information for a specific base model
def get_basemodel_info(username,password,modelinfo):
	uri = "https://stream.watsonplatform.net/speech-to-text/api/v1/models/"+modelinfo
	r = requests.get(uri, auth=(username,password), verify=False, headers=headers)
	respJson = r.json()
	print "List models returns: ", r.status_code
	print r.text

# Calling the main function.
if __name__ == '__main__':

	model_info = custom_model(username = username,password = password)
