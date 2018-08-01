/*
	Main driver script for the Speech to Text system
	utilizing Watson and ffmpeg.
*/

#include <string.h>
#include <iostream>
#include <vector>
#include <fstream>
#include <dirent.h>
#include <stdio.h>
#include <functional>
 #include <sys/stat.h>
using namespace std;


// Function definitions
bool exists( const string &);
const char *create_char_point(string);
bool check_extension(const string, const string);
void extract_audio(vector<string>);
void correct_name(vector<string> &);
string overlay(string &,string &,bool);

int main(int argc, char *argv[])
{

	if ( argc != 7 )
	{
		cerr << endl;
		cerr << "Usage: ./STT [Audio File 1] [Audio File 2] [Bluemix Username] [Bluemix Password]" 
		" [Speaker-1 Name] [Speaker-2 Name]\n";
		cerr << endl;
		return 0;
	}


	string file1_path = argv[1];
	string file2_path = argv[2];

	if (( exists(file1_path) == false ) || (exists(file2_path) == false))
	{
		cerr << "ERROR: File does not exist\n";
		return 0;
	}
	bool check1 = true,check2 = true;
	if ( ! check_extension(file1_path, "MXF") || ! check_extension(file2_path, "MXF"))
		check1 = false;
	if ( ! check_extension(file1_path, "wav") || ! check_extension(file2_path, "wav"))
		check2 = false;
	if (check1 == false && check2 == false )
	{
		cerr << "ERROR: Incorrect file extension. Ensure .MXF or >wav extension pair";
		return 0;
	}

	if ( check1 != false )
	{
		// Extracting the '.wav' audio from the MXF files.
		vector<string> all_files;
		all_files.push_back(file1_path);
		all_files.push_back(file2_path);
		correct_name(all_files);
		extract_audio(all_files);
	}

	// Overlaying the two newly generated audio files
	string new_name = overlay(file1_path,file2_path,check2);

	// Executing the main python transcribing script	
	string username = argv[3];
	string password = argv[4];
	string speaker1_name = argv[5];
	string speaker2_name = argv[6];
	string command = "python STT.py -credentials "+username+":"+password+" -model en-US_BroadbandModel"
	" -files "+file1_path+" "+file2_path+" -names "+speaker1_name+" "+speaker2_name+" -audio "+new_name;
	const char *command_final = create_char_point(command);
	system(command_final);



	return 0;
}


// Function exists
// Params: String byRef
// Does: Returns true if file exists
inline bool exists (const std::string& filename) {
  struct stat buffer;   
  return (stat (filename.c_str(), &buffer) == 0); 
}




// Function create_char_point
// Does: Convertes file name to dynamic a char pointer.
const char * create_char_point(string file_arg)
{
	const char *point = file_arg.c_str();
	return point;
}



// Function check_extension
// Does: Ensure that the file is an MXF file
bool check_extension(const string filename, const string ext)
{
	if (filename.substr(filename.find_last_of(".") +1) == ext)
		return true;
	else
		return false;
}




// Function correct_name
/*
	Re-adds the backslashes to file path if it 
	has been removed.
	Backslashes are removed from strings because 
	they are considered NULL references.

*/
void correct_name(vector<string> &all_files)
{
	for ( unsigned i = 0 ; i < all_files.size() ; i++ )
	{
		vector<char> curr_path;
		for ( unsigned k = 0 ; k < all_files[i].length() ; k++ )
			curr_path.push_back(all_files[i][k]);
		for ( unsigned j = 0 ; j < curr_path.size() ; j++ )
		{
			if ( curr_path[j] == ' ' && curr_path[j+1] == ' ')
			{
				break;
			}
			else if ( curr_path[j] == ' ')
			{
				curr_path.insert(curr_path.begin() + j, '\\');
				j++;
				
			}
		}
		std::string new_path(curr_path.begin(),curr_path.end());
		all_files[i] = new_path;
	}
}


void extract_audio(vector<string> all_files)
{
	string curr_path = all_files[0];
	string file2_path = all_files[1];
	string new_path;
	if ( curr_path.find("/") == std::string::npos)
	{
		std::size_t pos = curr_path.find_last_of(".");
		new_path = "./"+curr_path.substr(0,pos);
	}
	else
	{
		std::size_t pos = curr_path.find_last_of(".");
		std::size_t pos1 = curr_path.find_last_of("/");
		new_path = "."+curr_path.substr(pos1,pos-pos1);
	}
	string command = "ffmpeg -i "+ curr_path + " -map 0:1 -c copy "+ new_path +"-speaker1.wav -map 0:2 -c copy "+ new_path +"-speaker2.wav";
	const char *command_final = create_char_point(command);
	system(command_final);
}





// Function extract_audio
/*
	Calls the ffmpeg command to extract .wav
	files from every .MXF file 
*/
/*
void extract_audio(vector<string> all_files)
{
	for ( unsigned i = 0 ; i < all_files.size() ; i++ )
	{
		string curr_path = all_files[i];
		string new_path;
		if ( curr_path.find("/") == std::string::npos)
		{
			std::size_t pos = curr_path.find_last_of(".");
			new_path = "./"+curr_path.substr(0,pos);
		}
		else
		{
			std::size_t pos = curr_path.find_last_of(".");
			std::size_t pos1 = curr_path.find_last_of("/");
			new_path = "."+curr_path.substr(pos1,pos-pos1);
		}
		string command = "ffmpeg -i " + curr_path + " -map 0:1 -c copy " + new_path + "-speaker.wav";
		const char *command_final = create_char_point(command);
		system(command_final);
	}
}
*/

// Function overlay
// Params: The complete path to both audio files
// Does: Overlays the two audio files into a single 
//		 file.
string overlay(string & audio1, string & audio2, bool check2)
{
	string original_audio1 = audio1;
	string sub1, sub2;
	if ( audio1.find("/") == std::string::npos)
	{
		std::size_t pos = audio1.find_last_of(".");
		sub1 = audio1.substr(0,pos);
		if (check2 == false)
			audio1 = "./"+audio1.substr(0,pos)+ "-speaker1.wav";
		else
			audio1 = "./"+audio1.substr(0,pos)+ ".wav";
	}
	else
	{
		std::size_t pos = audio1.find_last_of(".");
		std::size_t pos1 = audio1.find_last_of("/");
		sub1 = audio1.substr(pos1+1,pos-pos1-1);
		if (check2 == false )
			audio1 = "."+audio1.substr(pos1,pos-pos1)+ "-speaker1.wav";
		else
			audio1 = "."+audio1.substr(pos1,pos-pos1)+ ".wav";
	}
	if ( audio2.find("/") == std::string::npos)
	{
		std::size_t pos = audio2.find_last_of(".");
		std::size_t pos2 = original_audio1.find_last_of(".");
		sub2 = audio2.substr(0,pos);
		if (check2 == false )
			audio2 = "./"+original_audio1.substr(0,pos2)+ "-speaker2.wav";
		else
			audio2 = "./"+audio2.substr(0,pos)+ ".wav";
	}
	else
	{
		std::size_t pos = audio2.find_last_of(".");
		std::size_t pos1 = audio2.find_last_of("/");
		std::size_t pos3 = original_audio1.find_last_of(".");
		std::size_t pos4 = original_audio1.find_last_of("/");
		sub2 = audio2.substr(pos1+1,pos-pos1-1);
		if (check2 == false )
			audio2 = "."+original_audio1.substr(pos4,pos3-pos4)+ "-speaker2.wav";
		else
			audio2 = "."+audio2.substr(pos1,pos-pos1)+ ".wav";
	}
	const string new_name = "./"+sub1 + "-" + sub2 + "-combined.wav";


	string command = "ffmpeg -i "+audio1+" -i "+audio2+ " -filter_complex amix=inputs=2:duration=longest:dropout_transition=3 "+new_name;

	const char *command_final = create_char_point(command);
	system(command_final);
	audio1 = audio1.erase(0,2);
	audio2 = audio2.erase(0,2);

	return new_name;

}


































