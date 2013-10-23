#!/usr/bin/python -u

from commands import getoutput
import snmp_passpersist as snmp
import subprocess
import datetime

base_oid = ".1.3.6.1.4.1234.1.3"

def get_data():
    raw_data = getoutput("cat cachetest.txt | awk '{print $6}'")
    return raw_data


def format_data(raw_data):
    formatted_data = []
    raw_data = raw_data.split("\n")
    for data in raw_data:
        if data and data != 'avg':
            formatted_data.append(data)
    return formatted_data


def collect_data():
    curr_time = datetime.datetime.now().strftime("%M")
    print curr_time
    cmd = ["nfsiostat", "2", "2"]
    with open('cachetest.txt', 'w') as outputfile:
        subprocess.call(cmd, stdout=outputfile)
        

def average_values(formatted_data):
    r = 0
    w = 0
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
    collect_data()
    raw_data = get_data()
    formatted_data = format_data(raw_data)
    r, w = average_values(formatted_data)
    print r,w
    
    pp.add_gau("1.1", r)
    pp.add_gau("1.2", w)
    
    print pp.data
    
pp = snmp.PassPersist(base_oid)
pp.start(update, 300)