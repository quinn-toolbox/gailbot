# Gailbot

GAILBOT will (G)enerate (A)n (I)nitiaL (B)allpark (O)rthographic (T)ranscript

## About Gailbot

Gailbot is named after [Gail Jefferson](https://en.wikipedia.org/wiki/Gail_Jefferson), inventor of the transcription system used for [Conversation Analysis](https://en.wikipedia.org/wiki/Conversation_analysis). She can generate a first pass at a transcript that can then be improved manually.

## How Gailbot works

Gailbot takea a recorded dialogue and uses [Watson's Speech-To-Text system](https://www.ibm.com/watson/services/speech-to-text/) to generate a transcript in the [CHAT transcription format](https://talkbank.org/manuals/CHAT.html). It then uses the [Jeffersonize](https://github.com/HiLabTufts/jeffersonize) tool to create a CA-like transcript that includes structural details of the talk such as intra-turn pauses, inter-turn gaps, and overlaps. 

## Status
Gailbot has been tested on MAC OSX.
The current version is an early alpha, feel free to provide feedback at: hilab-dev@elist.tufts.edu

## Before using gailbot

In order to use Gailbot, you should have some familiarity with using the terminal to install and run software. You should also be aware that after a certain amount of free time, IBM's Watson will begin to charge for automated transcription.

## Installation

1. Install ffmpeg either:

a) Using the [homebrew](https://brew.sh) packaging system:
* brew install ffmpeg

b) Using the binary:
* Download the installer from: https://www.ffmpeg.org/download.html
* Intall the tar file on the webpage using the instructions.
* Version required: 4.0.1 or later for Mac OSX.

2. Download and install the CLAN editor and CAfont from TalkBank:
* https://talkbank.org/software/

3. Build prerequisites
You'll need some python libraries, which can be installed using python's pip packaing system:

* easy_install pip

Then install the following libraries:
* pip install Watson-developer-cloud
* pip install pydub

4. Create an account with IBM so you can use Watson's speech-to-text service:
* You can sign up for a trial account here: console.bluemix.net/catalog/services/speech-to-text
* **Note**: Your IBM Bluemix username and password is required to establish a connection with Watson's Speech to Text service. For transcription pricing details see https://www.ibm.com/cloud/watson-speech-to-text/pricing

4. Download gailbot 
* Download or clone gailbot, then open a terminal and navigate to your gailbot directory.

## Usage

Use the following command to run gailbot:

* python driver.py -credentials [Bluemix Username]:[Bluemix Password] -files [one or two MXF/Wav file names] -names [One or two speaker names]
* Follow Gailbot's prompts to generate a transcript.

**NOTE:** Always copy and paste the custom model ID without punctuation marks when/if propmted by Gailbot.

## Options

**File Constraints**
Gailbot currently accepts '.wav' audio files and '.MXF' video files.

##  Custom and Acoustic Language Models:
Gailbot's Custom language model is meant to expand on Watson's existing word dictionary to transcribe specialized contexts. 
Users can add individual words, multiple words, or a corpus text file to the custom model. 
For more details: https://console.bluemix.net/docs/services/speech-to-text/language-resource.html#corporaWords

Gailbot's Acoustic language model is meant to train the service to recognize particular sound environments to improve the accuracy of the transcripts.
Currently, Gailbot allows a '.wav' file to train the custom acoustic model.
* The file must be less than 100 MB
* The file length must be greater than 10 minutes and less than 50 hours
* Must be a '.wav' file.

## Contribute

Please send feedback, bugs & requests to:
* hilab-dev@elist.tufts.edu

## Collaborators and Acknowledgments

The [HiLab](https://sites.tufts.edu/hilab/people/), including

* [Saul Albert](http://twitter.com/saul)
* [Jan P. Deruiter](http://twitter.com/jpderuiter)
* [Muhammad Umair](http://sites.tufts.edu/hilab/people)

