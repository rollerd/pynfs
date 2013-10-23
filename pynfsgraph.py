#!/usr/bin/python -u
from threading import Thread
import subprocess
import os.path
import snmp_passpersist as snmp
from commands import getoutput

OUTPUT_DATA = ['avg_RTT', 'avg_exe', 'kB/s']

base_oid=".1.3.6.1.4.1234.1.3"
COLUMN = {'ops/s': 1, "kB/s": 2, "kB/op": 3, "retrans": 4, "retrans_%": 5, "avg_RTT": 6, "avg_exe": 7}
THREAD_LIST = ["Place Holder"]
TOTAL_NFS_MOUNTS = 1


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


def collect_initial_data():
    cmd = ["nfsiostat", "1", "5"]
    with open('/home/roller/testdata.txt', 'w') as outputfile:
        subprocess.call(cmd, stdout=outputfile)


def format_data(data_type, mount_name_list):
    formatted_data = []
    count = 0
    raw_data = getoutput("cat /home/roller/testdata.txt | awk '{print $%d}'" % COLUMN[data_type]).split("\n")
    
    data_range = range(0, len(raw_data), 9)
    
    for start_point in data_range:
        data_point = raw_data[start_point : start_point + 9]
        data_point[1] = mount_name_list[count % TOTAL_NFS_MOUNTS]
        formatted_data.append(data_point)
        count += 1
    return formatted_data

        
def average_values(formatted_data):
    mount_data = {}
    for data_point in formatted_data:
        name = data_point[1]
        if name in mount_data:
            mount_data[name]['read'] += float(data_point[6])
            mount_data[name]['write'] += float(data_point[8])
            mount_data[name]['total'] += 1
        else:
            mount_data[name] = {'read': float(data_point[6]), 'write': float(data_point[8]), 'total': 1}
    
    averaged_mount_data = {}
    for mount in mount_data:
        total_read = mount_data[mount]['read']
        total_write = mount_data[mount]['write']
        total_items = mount_data[mount]['total']
        avg_read = total_read / total_items
        avg_write = total_write / total_items
        
        averaged_mount_data[mount] = {'avg_read': avg_read, 'avg_write': avg_write}

    return averaged_mount_data




def update():
    global THREAD_LIST
    mount_name_list = determine_number_of_mounts()
    mount_OID_list = []
    if THREAD_LIST[0]:
        THREAD_LIST.remove(THREAD_LIST[0])
    for data_type in OUTPUT_DATA:
        formatted_data = format_data(data_type, mount_name_list)
        averaged_data = average_values(formatted_data)


        for mount in averaged_data:
            if mount not in mount_OID_list:
                mount_OID_list.append(mount)
                mount_OID = mount_OID_list.index(mount) + 1
                data_OID = OUTPUT_DATA.index(data_type) * 2 + 1
                pp.add_gau("%s.%s" % (mount_OID, data_OID), str(averaged_data[mount]['avg_read']))
#                 print mount_OID, data_OID, str(averaged_data[mount]['avg_read'])
                data_OID += 1
                pp.add_gau("%s.%s" % (mount_OID, data_OID), str(averaged_data[mount]['avg_write']))
#                 print mount_OID, data_OID, str(averaged_data[mount]['avg_write'])
                
            else:
                mount_OID = mount_OID_list.index(mount) + 1
                data_OID = OUTPUT_DATA.index(data_type) * 2 + 1
                pp.add_gau("%s.%s" % (mount_OID, data_OID), str(averaged_data[mount]['avg_read']))
#                 print mount_OID, data_OID, str(averaged_data[mount]['avg_read'])
                data_OID += 1
                pp.add_gau("%s.%s" % (mount_OID, data_OID), str(averaged_data[mount]['avg_write']))
#                 print mount_OID, data_OID, str(averaged_data[mount]['avg_write'])

    thread_obj = Thread_Object()
    thread_obj.thread.start()
    
    THREAD_LIST.append(thread_obj)


class Thread_Object():
    def __init__(self):
        self.thread = Thread(target=self.run)
        self.thread.daemon = True
        
    def run(self):
        self.collect_data()
    
    def collect_data(self):
        cmd = ["nfsiostat", "1", "5"]
        with open('/home/roller/testdata.txt', 'w') as outputfile:
            subprocess.call(cmd, stdout=outputfile)
        outputfile.close()
        return 0


if not os.path.exists("/home/roller/testdata.txt"):
    collect_initial_data()


pp = snmp.PassPersist(base_oid)
pp.start(update, 6)

    
