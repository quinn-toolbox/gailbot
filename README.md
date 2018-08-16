# Gailbot
GAILBOT will Generate An InitiaL Ballpark Orthographic Transcript

Gailbot is designed to be a rough automated speech to text system that can make a first pass at generating Conversation Analystics (CA)
transcripts. It utlizes IBM's Watson Speech to Text API to generate a CHAT file in the CLAN editor, developed as part of Brian McWhinney's
(Carnigie Mellon University) Talk-Bank project. It further utilizes the Tufts Human Interaction Lab's Jeffersonize tool (https://github.com/HiLabTufts/jeffersonize) to generate a CAlite
representation of the transcript.

## Status
Gailbot has been tested on MAC OSX.
The current version is an early alpha, feel free to provide feedback at: hilab-dev@elist.tufts.edu

## Build
Run the following command on the command line to install Gailbot's pre-requisite libraries:
* pip install –upgrade Watson-developer-cloud
* pip install pydub

Install the ffmpeg tool:
* Download the tool from: ttps://www.ffmpeg.org/download.html
* Intall the tar file on the webpage using the instructions.
* Version required: 4.0.1 or later for Mac OSX.

Install the CLAN editor:
* https://talkbank.org/software/

## Usage

Follow these instructions after acquiring the aforementioned pre-requisites:
* Download or clone the repository, open the directory with a terminal.
* Use the following command to run gailbot:
  python driver.py -credentials [Bluemix Username]:[Bluemix Password] -files [one or two MXF/Wav file names] -names [One or two speaker names]
* Follow Gailbot's prompts to generate a transcript.

**NOTE:** Always copy and paste the custom model ID without punctuation marks when/if propmted by Gailbot.

**File Constraints**
As of yet, Gailbot only accepts '.wav' audio files and '.MXF' video files.

**Usage Constraints**
* Gailbot requires periodic monitoring of the command line output for responses to Gailbot's prompts/ any input that might be required.

**NOTE:** We do not, in any way, guarantee the accuracy of the trasnscripts generated from Gailbot. It is meantto generate prelimenary transcripts
that can them be improved through manual input.

##  Custom and Acoustic Language Models:
Gailbot's Custom language model is meant to expand on Watson's existing word dictionary to transcribe specialized contexts. 
Users can add individual words, multiple words, or a corpus text file to the custom model. For more details: https://console.bluemix.net/docs/services/speech-to-text/language-resource.html#corporaWords

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

* [Muhammad Umair](http://sites.tufts.edu/hilab/people) (Lead developer)
* [Saul Albert](http://twitter.com/saul)
* [Jan P. Deruiter](http://twitter.com/jpderuiter)

