#!/usr/bin/python -u
from threading import Thread
import subprocess
import os.path
import snmp_passpersist as snmp
from commands import getoutput

OUTPUT_MOUNT = ["127.0.0.1:/home/roller", "127.0.0.1:/home/roller/Desktop"]
OUTPUT_DATA = ['avg_RTT', 'avg_exe', 'kB/s']

BASE_OID = ".1.3.6.1.4.1234.1.3"
COLUMN = {'ops/s': 1, "kB/s": 2, "kB/op": 3, "retrans": 4, "retrans_%": 5, "avg_RTT": 6, "avg_exe": 7}
THREAD_LIST = ["Place Holder"]
TOTAL_NFS_MOUNTS = 1


def collect_initial_data():
    cmd = ["nfsiostat", "2", "145"]
    with open('/testing/testdata.txt', 'w') as outputfile:
        subprocess.call(cmd, stdout=outputfile)


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


def create_object_list(mount_name_list):
    object_list = []
    for name in mount_name_list:
        obj = Mount_Object(name)
        object_list.append(obj)
    
    return object_list


def get_raw_data(mount_name_list, field):
    column_data = []
    count = 0
    raw_data = getoutput("cat /testing/testdata.txt | awk '{print $%d}'" % COLUMN[field]).split("\n")
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

def remove_historic_data(raw_data):
    fields_to_remove = TOTAL_NFS_MOUNTS * 9
    formatted_data = raw_data[fields_to_remove :]
    return formatted_data

def add_data_to_objects(mount_object_list):
    for field in OUTPUT_DATA:
        field_data = get_raw_data(mount_name_list, field)
        for mount_data in field_data:
            for mount_object in mount_object_list:
                if mount_object.get_name() == mount_data[1]:
                    mount_object.add_data_point(field, mount_data)
          
    for obj in mount_object_list:
        obj.average_data()

    return mount_object_list


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
#                 print "%d.%d" % (mount_OID, data_OID), obj.get_name()
                for out_data in OUTPUT_DATA:
                    data_OID += 1
                    pp.add_gau("%d.%d" % (mount_OID, data_OID), str(obj.data()[out_data]['read']))
#                     print "%d.%d" % (mount_OID, data_OID), obj.data()[out_data]['read']
                    
                    data_OID += 1
                    pp.add_gau("%d.%d" % (mount_OID, data_OID), str(obj.data()[out_data]['write']))
#                     print "%d.%d" % (mount_OID, data_OID), obj.data()[out_data]['write']
        mount_OID += 1
    
        

    thread_obj = Thread_Object()
    thread_obj.thread.start()
    THREAD_LIST.append(thread_obj)
        



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


class Thread_Object():
    def __init__(self):
        self.thread = Thread(target=self.run)
        self.thread.daemon = True
        
    def run(self):
        self.collect_data()
    
    def collect_data(self):
        cmd = ["nfsiostat", "2", "145"]
        with open('/testing/testdata.txt', 'w') as outputfile:
            subprocess.call(cmd, stdout=outputfile)
        outputfile.close()
        return 0


if not os.path.exists("/testing/testdata.txt"):
    collect_initial_data()


mount_name_list = determine_number_of_mounts()
pp = snmp.PassPersist(BASE_OID)
pp.start(update, 300)
