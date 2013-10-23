#!/usr/bin/python -u
from threading import Thread
import sys
import subprocess
import os.path
import snmp_passpersist as snmp
from commands import getoutput
# import time

'''
BEFORE RUNING THIS SCRIPT, YOU SHOULD CONFIGURE THE BELOW OPTIONS (You may also pass the OUTPUT_MOUNT and OUTPUT_DATA args in from the command line/snmpd.conf):
ALSO NOTE: YOU SHOULD RUN SNMPWALK ONCE AFTER SETTING UP THE SCRIPT TO BEGIN COLLECTING DATA...(this is something that needs to be fixed)

OUTPUT_MOUNT should contain the list of mounts you wish to monitor. For example: OUTPUT_MOUNT = ["127.0.0.1:/home/user", "yukon6-h.wharton.private:/beaconprod/"]
You can find these names by running ./graphnfs.py --help

OUTPUT_DATA should contain the names of the data fields that you wish to export. A list of acceptable names can be found below:
["ops/s", "kB/s", "kB/op", "retrans", "retrans_%", "avg_RTT", "avg_exe"]
For example: OUTPUT_DATA = ['avg_RTT', 'avg_exe'] will export the read AND write data for both fields.

DATA_FILE is the path and filename where the collected data is written to (approx every 5 min)

The OIDs will be assigned to the mounts and data in the order in which they appear in the lists with the name of the mount always appearing in the .1 OID.
In the examples above, the OIDs would be:  
1.1 = 127.0.0.1:/home/user
1.2 = avg_RTT read
1.3 = avg_RTT write
1.4 = avg_exe read
1.5 = avg_exe write
2.1 = yukon6-h.wharton.private...
2.2 = avg_RTT read... etc
'''


OUTPUT_MOUNT = ["127.0.0.1:/EDIT ME/"]
OUTPUT_DATA = ['avg_RTT']
DATA_FILE = "/home/roller/workspace/pynfs/nfsdata.txt"



BASE_OID = ".1.3.6.1.4.1234.1.3"    #This is in the private branch and should not interfere with other snmp OIDs
COLUMN = {"ops/s": 1, "kB/s": 2, "kB/op": 3, "retrans": 4, "retrans_%": 5, "avg_RTT": 6, "avg_exe": 7}
THREAD_LIST = ["Place Holder"]
TOTAL_NFS_MOUNTS = 1

#Creates data file and starts collecting data on the first run of the script
def collect_initial_data():
    cmd = ["nfsiostat", "2", "145"]
    with open(DATA_FILE, 'w') as outputfile:
        subprocess.call(cmd, stdout=outputfile)

#Determines number of NFS mounts and returns a list of the name/path of each mount 
def determine_number_of_mounts():
    global TOTAL_NFS_MOUNTS
    mount_name_list = []
    lines = getoutput("nfsiostat").split("\n")    
    count = 0
    for line in lines:
        if 'mounted' in line:
            mount_name_list.append(line.split()[0])
            count += 1
    TOTAL_NFS_MOUNTS = count
    return mount_name_list

#Creates an object for each mount name and returns a list of these objects for use later
def create_object_list(mount_name_list):
    object_list = []
    for name in mount_name_list:
        obj = Mount_Object(name)
        object_list.append(obj)
    
    return object_list

#Returns a list containing the data from each selected field in OUTPUT_DATA and adds the name of the appropriate mount to each data point
def get_raw_data(mount_name_list, field):
    column_data = []
    count = 0
    raw_data = getoutput("cat " + DATA_FILE + " | awk '{print $%d}'" % COLUMN[field]).split("\n")
    raw_data = remove_historic_data(raw_data)
    data_range = range(9, len(raw_data), 9)
    for start_point in data_range:
        data_point = raw_data[start_point - 9 : start_point]
        if count > TOTAL_NFS_MOUNTS - 1:
            count = 0
        data_point[1] = mount_name_list[count]
        column_data.append(data_point)
        count += 1
    return column_data

#Removes the initial 'data since system start' that appears in a run of nfsiostat
def remove_historic_data(raw_data):
    fields_to_remove = TOTAL_NFS_MOUNTS * 9
    formatted_data = raw_data[fields_to_remove :]
    return formatted_data

#Adds the data from get_raw_data to each object in the object list according to name.
def add_data_to_objects(mount_object_list):
    for field in OUTPUT_DATA:
        field_data = get_raw_data(mount_name_list, field)
        for mount_data in field_data:
            for mount_object in mount_object_list:
                if mount_object.get_name() == mount_data[1]:
                    mount_object.add_data_point(field, mount_data)

    for obj in mount_object_list:
#         DEBUG_FILE = open('/home/roller/workspace/pynfs/datahistory.txt', 'a+')
        obj.average_data()
#         DEBUG_FILE.write(time.ctime() + "\n")
#         DEBUG_FILE.write(str(obj.data()['avg_RTT']['read']) + "\n")
#         DEBUG_FILE.write(str(obj.data()['avg_RTT']['write']) + "\n")
#         DEBUG_FILE.close()
    return mount_object_list

#Allows use of command line args to set OUTPUT_MOUNT and OUTPUT_DATA variables. Writes any bad args to nfserrorlog.txt
def set_args(argv, mount_name_list):
    global OUTPUT_MOUNT
    global OUTPUT_DATA
    if argv:
        OUTPUT_DATA = []
        OUTPUT_MOUNT = []
        for arg in argv:
            if arg == '--help':
                print 'NFS mounts on this system: '
                for name in mount_name_list:
                    print name
                print 'Data fields are: "ops/s", "kB/s", "kB/op", "retrans", "retrans_%", "avg_RTT", "avg_exe"\n'
                sys.exit(-1)
            if arg in COLUMN:
                OUTPUT_DATA.append(arg)
            elif arg in mount_name_list:
                OUTPUT_MOUNT.append(arg)
            else:
                errlog = open('/usr/local/bin/graphnfs/nfserrorlog.txt', 'w')
                errlog.write('"%s" is not a valid argument \n' % arg)
                errlog.write('Please use a valid mount path or data field - see script header or --help for details \n')
                errlog.write('Note - you will need to restart snmpd and run snmpwalk after making the changes to snmpd.conf')
                errlog.close()
                
#Runs every x seconds according to the interval set in pp.start and creates snmp OIDs. Also starts the data collection thread to prevent timeouts.
def update():
    global THREAD_LIST
    if THREAD_LIST[0]:
        THREAD_LIST.remove(THREAD_LIST[0])

    mount_object_list = create_object_list(mount_name_list)
    populated_object_list = add_data_to_objects(mount_object_list)

    mount_OID = 1

    for output_name in OUTPUT_MOUNT:
        data_OID = 0
        for obj in populated_object_list:
            if output_name == obj.get_name():
                data_OID += 1
                pp.add_str("%d.%d" % (mount_OID, data_OID), obj.get_name())
                for out_data in OUTPUT_DATA:
                    data_OID += 1
                    pp.add_gau("%d.%d" % (mount_OID, data_OID), str(obj.data()[out_data]['read']))
                    
                    data_OID += 1
                    pp.add_gau("%d.%d" % (mount_OID, data_OID), str(obj.data()[out_data]['write']))
        mount_OID += 1
    

    thread_obj = Thread_Object()
    thread_obj.thread.start()
    THREAD_LIST.append(thread_obj)
        

#Class for creating the mount objects. 
class Mount_Object():
    def __init__(self, name):
        self.name = name
        self.total_data_points = 0
        self.data_point_dict = {}
        
    def get_name(self):
        return self.name
    
    def data(self):
        return self.data_point_dict
  
    def add_data_point(self, field, data):
        if field in self.data_point_dict:
            self.data_point_dict[field]['read'] += float(data[6])
            self.data_point_dict[field]['write'] += float(data[8])
        else:
            self.data_point_dict[field] = {'read' : float(data[6]), 'write' : float(data[8])}
        self.total_data_points += 1.0
    
    def average_data(self):
        self.total_data_points /= len(self.data_point_dict)
        for field in self.data_point_dict:
            self.data_point_dict[field]['read'] /= self.total_data_points
            self.data_point_dict[field]['write'] /= self.total_data_points


#This object is created each time data needs to be collected in a new thread.
class Thread_Object():
    def __init__(self):
        self.thread = Thread(target=self.run)
        self.thread.daemon = True
        
    def run(self):
        self.collect_data()
    
    def collect_data(self):
        cmd = ["nfsiostat", "2", "145"]
        with open(DATA_FILE, 'w') as outputfile:
            subprocess.call(cmd, stdout=outputfile)
        outputfile.close()
        return 0


if __name__ == '__main__':   
    #If the initial data file does not exist, creates and populates it.
    if not os.path.exists(DATA_FILE):
        collect_initial_data()
    
    mount_name_list = determine_number_of_mounts()
    set_args(sys.argv[1:], mount_name_list) 
    pp = snmp.PassPersist(BASE_OID)
    pp.start(update, 300)
