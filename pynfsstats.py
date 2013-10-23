#!/usr/bin/python -u
from commands import getoutput
import re
import snmp_passpersist as snmp

base_oid = ".1.3.6.1.4.1234.1.3"                #.1.3.6.1.4... is in the private branch
TOTAL_NFS_MOUNTS = 1
#Enter the fields whose data you would like to output below
FIELDS_TO_OUTPUT = ['read_avg RTT (ms)', 'write_avg RTT (ms)', 'read_avg exe (ms)', 'write_avg exe (ms)']

def determine_number_of_shares():                #Attempt to determine number of shares by looking for 'mounted' keyword. Should only appear once per share
    global TOTAL_NFS_MOUNTS
    lines = getoutput("nfsiostat").split("\n")    
    count = 0
    for line in lines:
        if 'mounted' in line:
            count += 1
    TOTAL_NFS_MOUNTS = count


def parse_data():                                #Formats the raw data and strips away the 'since system start' data that is output for each nfs mount on the first output
    list_of_split_lines = []

    lines = getoutput("nfsiostat 1 2").split("\n")        #split raw nfsiostat data on \n
    for line in lines:
        line = re.sub(r'\s{4,}', "\t", line)            #If any line has more than 4 spaces in a row in it, subtitute them for a tab \t (some nfsiostat data is tabbed, some is spaced...why?)
        line = line.split("\t")                            #Split strings further on tab \t
        list_of_split_lines.append(line)                #Add newly split fields to list - now have a list of lists
    
    data_only = []
    for each_list in list_of_split_lines:                #Removes any list items that are 'empty' ''  or that don't have data and removes whitespace from data
        for data in each_list:
            if data:
                data = data.strip()                
                data_only.append(data)

    count = 0
    while count < TOTAL_NFS_MOUNTS:                        #Removes the 'since boot' data that is produced by nfsiostat on the first output for each mount
        discard, data_only = trim_list(data_only, 'mounted')
        count += 1
    return data_only


def trim_list(orig_list, word_to_trim_on):                #takes a list and keyword where list will be split
    index_cutoff = 0                                    #We use this function to remove the 'since boot' data as well as for splitting and returning the data used for the NFS_Mount objects
    current_index = 0                                    #Returns the SECOND occurrence of the word_to_trim_on, since we split on that word and also return it as the first item
    skip_first = True
    before_cut = []
    after_cut = []
    for item in orig_list:
        if word_to_trim_on in item:
            if not skip_first:
                index_cutoff = current_index
                after_cut = orig_list[index_cutoff:]
                before_cut = orig_list[:index_cutoff]
                return  before_cut, after_cut
            else:
                skip_first = False
        current_index += 1
    after_cut = orig_list[index_cutoff:]
    before_cut = orig_list[:index_cutoff]
    return before_cut, after_cut


def create_objects():                                    #Create nfs_mount objects with appropriate data and adds them to a list
    object_list = []
    data = parse_data()
    if TOTAL_NFS_MOUNTS == 1:
        nfs_data_object = NFS_Mount(data)
        object_list.append(nfs_data_object)
    else:
        for i in range(0, TOTAL_NFS_MOUNTS - 1):        #subtract one from total num mounts so that we dont try to trim the list with only one element left
            beginning, data = trim_list(data, 'mounted')
            nfs_data_object = NFS_Mount(beginning)
            object_list.append(nfs_data_object)
        nfs_data_object = NFS_Mount(data)
        object_list.append(nfs_data_object)
    
    return object_list
    

class NFS_Mount():                            #class that maps the data for each mount to a dictionary for use later
    
    def __init__(self, data):
        self.name = data[0]
        self.data_dict = {}
        self.create_dict(data)
        
    def create_dict(self, data):            #Just creates a dictionary mapping the names to values using the offset for each section of the data list
        self.data_dict["name"] = data[0]
        for i in range(1, 3):
            self.data_dict["cpu_" + data[i]] = data[i + 2]
        for i in range(6, 12):
            self.data_dict["read_" + data[i]] = data[i + 6]
        for i in range(19, 25):
            self.data_dict["write_" + data[i]] = data[i + 6]
    
    def print_all_data(self):                #for testing
        print self.data_dict
        
    def get_data(self, data_name):            
        return self.data_dict[data_name]


def update():                                #creates the oid tree numbers and adds the selected data 
    determine_number_of_shares()
    object_list = create_objects()
    
    obj_count = 1                           #Each object(nfs mount) will have its own 'base' number followed by 
    for obj in object_list:                 #the number for the actual data. ie 2.1 (object 2, data point 1), 2.2, 2.3, etc
        data_num = 0                        #The data number will follow the order set in the FIELDS_TO_OUTPUT global variable
        for field in FIELDS_TO_OUTPUT:
            data_num += 1
#             pp.add_str("%s.%s" % (str(obj_count), str(data_num)), field)        #This section will output the name or key associated with the data. Not necessary for now
#             data_num += 1
            pp.add_gau("%s.%s" % (str(obj_count), str(data_num)), float(obj.get_data(field)))
        obj_count += 1

pp = snmp.PassPersist(base_oid)
pp.start(update, 290)

