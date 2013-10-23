#!/usr/bin/python -u
from threading import Thread
import subprocess
import os.path
import snmp_passpersist as snmp
from commands import getoutput

OUTPUT_DATA = ["avg_RTT"]
base_oid = ".1.3.6.1.4.1234.1.3"
THREAD_LIST = ["Place Holder"]
COLUMN = {'ops/s': 1, "kB/s": 2, "kB/op": 3, "retrans": 4, "retrans_%": 5, "avg_RTT": 6, "avg_exe": 7}

def collect_initial_data():
    cmd = ["nfsiostat", "2", "145"]
    with open('/home/roller/testing.txt', 'w') as outputfile:
        subprocess.call(cmd, stdout=outputfile)
        

def format_data(data_type):
    formatted_data = []
    raw_data = getoutput("cat /home/roller/testing.txt | awk '{print $%d}'" % COLUMN[data_type]).split("\n")
    for data in raw_data:
        if data and data != 'avg':
            formatted_data.append(data)
    return formatted_data


def average_values(formatted_data):
    r = 0.0
    w = 0.0
    for i in range(0, len(formatted_data)):
        if i % 2 == 0:
            r += float(formatted_data[i])
        else:
            w += float(formatted_data[i])
    
    total = len(formatted_data) / 2        
    
    r = r / total
    w = w / total
    return r, w


def update():
    global THREAD_LIST
    
    if THREAD_LIST[0]:
        THREAD_LIST.remove(THREAD_LIST[0])
        
    formatted_data = format_data(OUTPUT_DATA[0])
    r, w = average_values(formatted_data)

    pp.add_gau("1.1", str(r))
    pp.add_gau("1.2", str(w))

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
        cmd = ["nfsiostat", "2", "145"]
        with open('/home/roller/testing.txt', 'w') as outputfile:
            subprocess.call(cmd, stdout=outputfile)
        outputfile.close()
        return 0
        

if not os.path.exists("/home/roller/testing.txt"):
    collect_initial_data()


pp = snmp.PassPersist(base_oid)
pp.start(update, 300)   
