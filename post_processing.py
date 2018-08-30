import csv
from operator import itemgetter
from subprocess import call
import time
import io
import sys
import base64                      # necessary to encode in base64
from subprocess import call
import itertools



# Function that assigns threshold values
# based on the audio quality.
# The user can also choose to manually set all 
# thresholds.
'''
As of yet, the thresholds that can be changed are:
    1. Normal pauses.
    2. Micro pauses
    3. Normal gaps.
    4. Very large pauses
    5. Latch markers
    6. TCU break point
Default values are initialized to global variables.
'''
def customize_thresholds(flag):
    if flag == False:
        normal_gap = 0.3
        latch_low = 0.01
        latch_high = 0.05
        normal_pause_low = 0.2
        normal_pause_high = 1.0
        micropause_low = 0.1
        micropause_high = 0.2
        very_large_pause = 1.0
        TCU_break = 0.1
    else:

        while True:
            option = raw_input('Press 1 to specify slow speech rate\nPress 2 to specify medium speech rate\nPress 3 to specify high speech rate\nPress 4 to customize individual thresholds\nPress 5 for default values\n')
            if option == '1':
                normal_gap = 0.4
                latch_low = 0.02
                latch_high = 0.06
                normal_pause_low = 0.3
                normal_pause_high = 1.1
                micropause_low = 0.2
                micropause_high = 0.3
                very_large_pause = 1.1
                TCU_break = 0.11
                break

            elif option == '2':
                normal_gap = 0.3
                latch_low = 0.01
                latch_high = 0.05
                normal_pause_low = 0.2
                normal_pause_high = 1.0
                micropause_low = 0.1
                micropause_high = 0.2
                very_large_pause = 1.0
                TCU_break = 0.1
                break

            elif option == '3':
                normal_gap = 0.2
                latch_low = 0
                latch_high = 0.04
                normal_pause_low = 0.1
                normal_pause_high = 0.9
                micropause_low = 0
                micropause_high = 0.1
                very_large_pause = 0.9
                TCU_break = 0.09
                break

            elif option == '4':
                print('NOTE: All threshold values should be in seconds')
                print('Specify normal gap threshold')
                normal_gap = get_float_int_input()
                print('Specify lower bound for latch marker')
                latch_low = get_float_int_input()
                print('Specify upper bound for latch marker')
                latch_high = get_float_int_input()
                print('Specify lower bound for normal pause')
                normal_pause_low = get_float_int_input()
                print('Specify upper bound for normal pause')
                normal_pause_high = get_float_int_input()
                print('Specify lower bound for micro-pauses')
                micropause_low = get_float_int_input()
                print('Specify upper bound for micro-pauses')
                micropause_high = get_float_int_input()
                print('Specify threshold for very large pauses')
                very_large_pause = get_float_int_input()
                print('Specify TCU break-off threshold')
                TCU_break = get_float_int_input()
                break

            elif option == '5':
                normal_gap = 0.3
                latch_low = 0.01
                latch_high = 0.05
                normal_pause_low = 0.2
                normal_pause_high = 1.0
                micropause_low = 0.1
                micropause_high = 0.2
                very_large_pause = 1.0
                TCU_break = 0.1
                break

    thresholds = {'ng': normal_gap, 'll': latch_low, 'lh' : latch_high, 'npl' : normal_pause_low, 'nph' : normal_pause_high, 'ml' : micropause_low, 'mh' : micropause_high, 'vlp' : very_large_pause, 'break' : TCU_break}
    return thresholds

# Function that declares thresholds as global variables
def dec_global_thresholds(thresh_dict):
    global normal_gap
    global latch_low
    global latch_high
    global normal_pause_low
    global normal_pause_high
    global micropause_low
    global micropause_high
    global very_large_pause
    global TCU_break
    normal_gap = thresh_dict['ng']
    latch_low = thresh_dict['ll']
    latch_high = thresh_dict['lh']
    normal_pause_low = thresh_dict['npl']
    normal_pause_high = thresh_dict['nph']
    micropause_low = thresh_dict['ml']
    micropause_high = thresh_dict['mh']
    very_large_pause = thresh_dict['vlp']
    TCU_break = thresh_dict['break']


# Helper function that gets float or interger input only
def get_float_int_input():
    count = 0
    while True:
        number = raw_input()
        nb = None
        for cast in (int, float):
            try:
                nb = cast(number)
                if nb != None:
                    number = cast
                    return nb
            except ValueError:
                count+=1
                if count == 2:
                    print('Error: Ensure integer or float input. Re-Enter input')

# Function that reads data from a single csv file
def read_data_single(file1):
	data1 = []
	with open(file1,'rb') as f:
		reader = csv.reader(f)
		data = list(reader)
		for item in data:
			item[1] = float(item[1])
			item[2] = float(item[2])
			data1.append(item)
	all_data = data1
	return all_data	


# Function that reads the csv data for post_processig
def read_data_double(file1,file2):
	data1 = []
	data2 = []
	with open(file1,'rb') as f:
		reader = csv.reader(f)
		data = list(reader)
		for item in data:
			item[1] = float(item[1])
			item[2] = float(item[2])
			data1.append(item)
	with open(file2,'rb') as f:
		reader = csv.reader(f)
		data  = list(reader)
		for item in data:
			item[1] = float(item[1])
			item[2] = float(item[2])
			data2.append(item)

	all_data = [data1,data2]
	return all_data




# Function that does pos-processing on the seperate 
# speaker CSV files.
def seperate_postprocessing(all_lines,thresh_dict):
    all_lines = remove_confidence(all_lines)
    all_lines = create_utterances(all_lines,thresh_dict['break'])
    return all_lines


# Function that removes the confidence 
# data for individual speakers
def remove_confidence(all_lines):
    for item in all_lines:
        del item[-1]
    return all_lines


# Function that creates utterances based on a threshold for
# the individual speakers.
def create_utterances(all_lines,threshold):
    new_lines = []
    count = 0
    new = True
    changed = False
    while count < len(all_lines)-1:
        curr_end = all_lines[count][2]
        nxt_start = all_lines[count+1][1]
        diff = nxt_start - curr_end
        if diff <= threshold or diff == 0:
            changed = True
            new_trans = all_lines[count][-1]+u''+all_lines[count+1][-1]
            all_lines[count][-1] = new_trans
            all_lines[count][2] = all_lines[count+1][2]
            if len(new_lines) > 0  and len(new_lines[-1][-1].split()) > 1:
                new_lines[-1] = [all_lines[count][0],all_lines[count][1],all_lines[count+1][2],new_trans]
            else:
                new_lines.append([all_lines[count][0],all_lines[count][1],all_lines[count+1][2],new_trans])
            del all_lines[count+1]
            if count >= len(all_lines):
                return new_lines
        else:
            if  changed ==  False:
                new_lines.append(all_lines[count])
            else:
                new_lines.append(all_lines[count+1])
            count+=1
    return new_lines


# Function that combines and does postprocessing on
# the two seperately created CSV files
def combined_postprocessing(data1,data2,thresh_dict):
    dec_global_thresholds(thresh_dict)
    all_lines = combined_concat(data1,data2)
    all_lines = extra_spaces(all_lines)
    all_lines = overlaps(all_lines)
    all_lines = pauses(all_lines)
    all_lines = add_end_spacing(all_lines)
    all_lines = combined_same_concat(all_lines)
    all_lines = eol_delim(all_lines)

    #all_lines = rem_very_large_pause(all_lines)

    all_lines = rem_pause_ID(all_lines)
    all_lines = comment_hesitation(all_lines)
    all_lines = gaps(all_lines)
    all_lines = extra_spaces(all_lines)
    all_lines = extra_spaces(all_lines)

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
        prev_trans = unicode(prev_item[-1])
        curr_name = curr_item[0]
        prev_name = prev_item[0]
        curr_trans = unicode(curr_item[-1])
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
        if second_last_end > prev_end:
            prev_end = second_last_end
        diff = curr_start - prev_end
        diff = round(diff,1)
        if curr_name != prev_name and curr_name != '*PPP':
            # Normal gap
            if diff > normal_gap:
                new_item = [' ', prev_end , curr_start , '\t('+str(diff)+') . ']
                all_lines.insert(count,new_item)
                pos = prev_trans.rfind('.')
                if pos != -1:
                    if prev_trans[pos+1].isnumeric() == False or prev_trans[pos+1] != ')':
                        prev_trans = prev_trans[:pos-1]+prev_trans[pos+1:]
                all_lines[count-1][-1] = prev_trans
                count+=1
            # Adding the latch markers
            elif diff > latch_low and diff < latch_high: 
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




# Function that adds spacing to the start and end of 
# an utterance
def add_end_spacing(all_lines):
    for item in all_lines:
        trans = item[-1]
        trans = ' '+trans+' '
        item[-1] = trans
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

                # Case 1:
                # sbt is positive means overlap starts at position x from start of 
                # utterance 1 but at the start of utterance 2
                if start_boundary_time > 0:
                    x = (abs(start_boundary_time)/(all_lines[count][2]-all_lines[count][1]))*100
                    x = (x/100)*len(all_lines[count][-1])
                    x = int(round(x))
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
                        y = 100-((abs(end_boundry_time))/(all_lines[count][2]-all_lines[count][1])*100)
                        y = (y/100)*len(all_lines[count][-1])
                        y = int(round(y))
                        utt_1_overlap_end = y
                        # Adding the overlap character limit
                        if utt_1_overlap_end - utt_1_overlap_start <= limit:
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        all_lines[count][-1] = all_lines[count][-1][:utt_1_overlap_end]+'!'+all_lines[count][-1][utt_1_overlap_end:]
                        all_lines[count+1][-1] = all_lines[count+1][-1]+'@'

                    # Case 1 b:
                        # ebt is negative means that overlap ends at utterance 1 end
                        # and that overlap ends at position y from utterance 2 end.
                    elif end_boundry_time < 0:
                        y = 100-((abs(end_boundry_time)/(all_lines[count+1][2]-all_lines[count+1][1]))*100)
                        y = (y/100)*len(all_lines[count+1][-1])
                        y = int(round(y))
                        utt_2_overlap_end = y 
                        # Adding the overlap character limit
                        if len(all_lines[count][-1])-utt_1_overlap_start <= limit:
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        if utt_2_overlap_end - 0 <= limit:
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        all_lines[count][-1] = all_lines[count][-1]+'!'
                        all_lines[count+1][-1] = all_lines[count+1][-1][:utt_2_overlap_end]+'@'+all_lines[count+1][-1][utt_2_overlap_end:]

                    # Case 1 c:
                        # ebt is 0 means that the overlap ends at both utterances end
                    elif end_boundry_time == 0:
                        all_lines[count][-1] = all_lines[count][-1] + '!'
                        all_lines[count+1][-1] = all_lines[count+1][-1] +'@'

                # Case 2:
                # Sbt is negative means that overlap starts from start of utterance 1
                # and position x  of utterance 2.
                elif start_boundary_time < 0:

                    x = (abs(start_boundary_time)/(all_lines[count+1][2]-all_lines[count+1][1]))*100
                    x = (x/100)*len(all_lines[count+1][-1])
                    x = int(round(x))

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
                        y = 100-((abs(end_boundry_time)/(all_lines[count][2]-all_lines[count][1]))*100)
                        y = (y/100)*len(all_lines[count][-1])
                        y = int(round(y))
                        utt_1_overlap_end = y
                        if utt_1_overlap_end - 0 <= limit:
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        if len(all_lines[count+1][-1])-utt_2_overlap_start <= limit:
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        all_lines[count][-1] = all_lines[count][-1][:utt_1_overlap_end]+'!'+all_lines[count][-1][utt_1_overlap_end:]
                        all_lines[count+1][-1] = all_lines[count+1][-1]+'@'


                    # Case 2 b:
                        # ebt is negative means that overlap ends at utterance 1 end
                        # and that overlap ends at position y from utterance 2 end.
                    elif end_boundry_time < 0:
                        y = 100-((abs(end_boundry_time)/(all_lines[count+1][2]-all_lines[count+1][1]))*100)
                        y = (y/100)*len(all_lines[count+1][-1])
                        y = int(round(y))
                        utt_2_overlap_end = y
                        if utt_2_overlap_end- utt_2_overlap_start <= limit:
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        all_lines[count][-1] = all_lines[count][-1]+'!'
                        all_lines[count+1][-1] = all_lines[count+1][-1][:utt_2_overlap_end]+'@'+all_lines[count+1][-1][utt_2_overlap_end:]

                    # Case 2 c:
                        # ebt is 0 means that overlap ends at both utterances end.
                    elif end_boundry_time == 0:
                        all_lines[count][-1] = all_lines[count][-1] + '!'
                        all_lines[count+1][-1] = all_lines[count+1][-1] +'@'

                # Case 3: 
                # sbt is 0 means that the overlap starts from the start of both turns.
                elif start_boundary_time == 0:
                    orig1 = all_lines[count][-1]
                    orig2 = all_lines[count+1][-1]
                    all_lines[count][-1] = '<'+all_lines[count][-1]
                    all_lines[count+1][-1] = '<'+all_lines[count+1][-1]

                    # Case 3 a: 
                        # ebt is positive means that overlap ends at position y from 
                        # utterance one start and overlaps end at end position of 
                        # utterance 2
                    if end_boundry_time > 0:
                        y = 100-((abs(end_boundry_time)/(all_lines[count][2]-all_lines[count][1]))*100)
                        y = (y/100)*len(all_lines[count][-1])
                        y = int(round(y))
                        utt_1_overlap_end = y
                        if utt_1_overlap_start - 0 <= limit:
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        all_lines[count][-1] = all_lines[count][-1][:utt_1_overlap_end]+'!'+all_lines[count][-1][utt_1_overlap_end:]
                        all_lines[count+1][-1] = all_lines[count+1][-1]+'@'

                    # Case 3 b:
                        # ebt is negative means that overlap ends at utterance 1 end
                        # and that overlap ends at position y from utterance 2 end.
                    elif end_boundry_time < 0:
                        y = 100-((abs(end_boundry_time)/(all_lines[count+1][2]-all_lines[count+1][1]))*100)
                        y = (y/100)*len(all_lines[count+1][-1])
                        y = int(round(y))
                        utt_2_overlap_end = y
                        if utt_2_overlap_end - 0 <= limit:
                            all_lines[count][-1] = orig1
                            all_lines[count+1][-1] = orig2
                            count+=1
                            continue
                        all_lines[count][-1] = all_lines[count][-1]+'!'
                        all_lines[count+1][-1] = all_lines[count+1][-1][:utt_2_overlap_end]+'@'+all_lines[count+1][-1][utt_2_overlap_end:]

                    # Case 3 c:
                        # ebt is 0 means that overlap ends at both utterances end.
                    elif end_boundry_time == 0:
                        all_lines[count][-1] = all_lines[count][-1] + '!'
                        all_lines[count+1][-1] = all_lines[count+1][-1] +'@' 
                count+=1
            else:
                count+=1

        elif all_lines[count+1][0] == '*PPP':
            count+=2
        elif all_lines[count][0] == all_lines[count+1][0]:
            count+=1

    for item in all_lines:
        trans = item[-1]
        count = 0
        while count < len(trans):
            if trans[count] == '<' and count != 0 and trans[count+1] != ']': 
                trans = trans[:count]+trans[count+1:]
                pos = trans.rfind(' ',0,count)
                if pos == -1:
                    pos = 0
                if pos != 0:
                    trans = trans[:pos+1]+'<'+trans[pos+1:]
                else:
                    trans = trans[:pos]+'<'+trans[pos:]
            elif trans[count] == '!':
                trans = trans[:count]+trans[count+1:]
                pos = trans.find(' ',count,len(trans))
                if pos == -1:
                    pos = len(trans)
                trans = trans[:pos]+'!'+trans[pos:]
            elif trans[count] == '@':
                trans = trans[:count]+trans[count+1:]
                pos = trans.find(' ',count,len(trans))
                if pos == -1:
                    pos = len(trans)
                trans = trans[:pos]+'@'+trans[pos:]
            count+=1
        trans = trans.replace('!','> [>] ')
        trans = trans.replace('@','> [<] ')
        item[-1] = trans


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
                    count+=1
                new_trans += overlap_marker
                new_trans += pause_marker+')'
            else:
                new_trans += trans[count]

            count+=1
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
        prev_trans = unicode(prev_item[-1])
        curr_name = curr_item[0]
        prev_name = prev_item[0]
        if count > 2:
            second_last_end = all_lines[count-2][2]
        else:
            second_last_end = curr_start
        if second_last_end == None:
            second_last_end = curr_start
        if count < 0:
            prev_end = curr_start
        if prev_end == None:
            prev_end = curr_start
        if second_last_end > prev_end and count > 2:
            special = True
        diff = curr_start - prev_end
        diff = round(diff,1)
        if curr_name == prev_name:
            # Normal pause
            if (diff > normal_pause_low and diff <= normal_pause_high):
                prev_trans += ' ('+str(diff)+') '
                all_lines[count-1][-1] = prev_trans
            # Micropauses
            elif diff > micropause_low and diff < micropause_high:
                prev_trans += ' (.) '
                all_lines[count-1][-1] = prev_trans
            # Very large pauses
            elif diff > very_large_pause or special == True: 
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
        prev_trans = unicode(prev_item[-1])
        curr_name = curr_item[0]
        prev_name = prev_item[0]
        curr_trans = unicode(curr_item[-1])
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


# Function that gets header values to be used
# for building CHAT file
def define_headers(flag):
    if flag == False:
        corpus_name = 'In_Conversation_Corpus'
        language = 'eng'
        speaker1_gender = 'male'
        speaker2_gender = 'male'
        corpus_location = 'Hi_Lab'
        location = 'HI Lab'
        room_layout = 'Hi Lab duplex'
        situation = 'Laboratory'
        speaker1_role = 'Unidentified'
        speaker2_role = 'Unidentified'
    else:
        corpus_name = raw_input('Specify the corpus name\n')
        language = raw_input('Specify the language code\n')
        speaker1_gender = raw_input("Specify the first speaker's gender\n")
        speaker1_role = raw_input('Specify speaker 1 role\n')
        speaker2_gender = raw_input("Specify the second speaker's gender\n")
        speaker2_role = raw_input('Specify speaker 2 role\n')
        corpus_location = raw_input('Specify the location where corpus was created\n')
        location = raw_input('Specify the current location\n')
        room_layout = raw_input('Specify the room layout\n')
        situation = raw_input('Specify the situation\n')

    headers_CHAT = {'corpus_name':corpus_name,'language':language,'speaker1_gender': speaker1_gender, 'speaker2_gender' : speaker2_gender, 'corpus_location' : corpus_location, 'room_layout' : room_layout, 'situation': situation, 'location':location,'role1':speaker1_role,'role2':speaker2_role}
    return headers_CHAT



# Function that builds a CHAT file from 
# data formatted for the CSV format
def build_CHAT(all_lines,name1,name2,audio_name,flag,out_dir_name):
    for item in all_lines:
        item = [unicode(x) for x in item]
    id1 = name1[:3].upper()
    id2 = name2[:3].upper()
    if id1 == id2:
        id1 = id1[:2]+'1'
        id2 = id2[:2]+'2'
    with io.open(out_dir_name+'combined.cha',"w",encoding = 'utf-8') as outfile:
        headers = define_headers(flag)
        outfile.write(u'@Begin\n@Languages:\t'+headers['language']+'\n@Participants:\t')
        outfile.write(unicode(id1)+u' '+unicode(name1)+u' '+headers['role1']+', '+unicode(id2)+u' '+unicode(name2)+u' '+headers['role2']+'\n')
        outfile.write(u'@Options:\tCA\n')
        outfile.write(u'@ID:\t'+headers['language']+'|'+headers['corpus_name']+'|'+unicode(id1)+'||'+headers['speaker1_gender']+'|||'+headers['role1']+'|||'+'\n')
        outfile.write(u'@ID:\t'+headers['language']+'|'+headers['corpus_name']+'|'+unicode(id2)+'||'+headers['speaker2_gender']+'|||'+headers['role2']+'|||'+'\n')
        outfile.write(u'@Media:\t'+unicode(audio_name)+u',audio\n')
        outfile.write(u'@Comment:\t'+headers['corpus_name']+', '+headers['corpus_location']+'\n')
        outfile.write(u'@Transcriber:\tSTT_system\n@Location:\t'+headers['location']+'\n@Room Layout:\t'+headers['room_layout']+'\n')
        outfile.write(u'@Situation:\t'+headers['situation']+'\n@New Episode\n')
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



def combined_post_processing_single(all_lines,thresh_dict):
    dec_global_thresholds(thresh_dict)
    all_lines = extra_spaces(all_lines)
    all_lines = overlaps(all_lines)
    all_lines = pauses(all_lines)
    all_lines = add_end_spacing(all_lines)
    all_lines = combined_same_concat(all_lines)
    all_lines = eol_delim(all_lines)
    all_lines = rem_pause_ID(all_lines)
    all_lines = comment_hesitation(all_lines)
    all_lines = gaps(all_lines)
    all_lines = extra_spaces(all_lines)
    all_lines = extra_spaces(all_lines)
    return all_lines




# Function that removes a line with very large pause
def rem_very_large_pause(all_lines):
    count = 0
    new_lines = []
    while count < len(all_lines):
        if all_lines[count][0] != '*PPP':
            new_lines.append(all_lines[count])
        count+=1
    return new_lines





















