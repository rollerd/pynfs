from commands import getoutput
import snmp_passpersist as snmp
import subprocess
import datetime

TOTAL_NFS_MOUNTS = 1
base_oid = ".1.3.6.1.4.1234.1.3"

def determine_number_of_mounts():                #Attempt to determine number of mounts by looking for 'mounted' keyword. Should only appear once per share
    global TOTAL_NFS_MOUNTS
    lines = getoutput("nfsiostat").split("\n")    
    count = 0
    for line in lines:
        if 'mounted' in line:
            count += 1
    TOTAL_NFS_MOUNTS = count


def remove_historic_data(data_set):
    start_index = (TOTAL_NFS_MOUNTS * 2)
    data_set = data_set[start_index:]
    return data_set
        

def collect_data():
    curr_time = datetime.datetime.now().strftime("%M")
    print curr_time
    cmd = ["nfsiostat", "2", "145"]
    with open("nfscachedata.txt", 'w') as outputfile:
        subprocess.call(cmd, stdout=outputfile)
    outputfile.close()
        
    
    
def parse_data():
    just_data = []
    data_only = getoutput("cat nfscachedata.txt | awk '{print $6}'")
    data_only = data_only.split("\n")
    
    for line in data_only:
        if line and line != 'avg':
            line = line.strip()
            just_data.append(float(line))
            
    just_data = remove_historic_data(just_data)
    read = 0.0
    write = 0.0
    
    for i in range(0, len(just_data)):
        if i % 2 == 0:
            read += just_data[i]
        else:
            write += just_data[i]
    
    num_data_points = len(just_data) / 2
    avg_read = float("{0:.2f}".format(read / num_data_points))
    avg_write = float("{0:.2f}".format(write / num_data_points))
            
    return avg_read, avg_write


def update():
    determine_number_of_mounts()
    collect_data()
    avg_read, avg_write = parse_data()
    pp.add_gau("1.1", avg_read)
    pp.add_gau("1.2", avg_write)



pp = snmp.PassPersist(base_oid)
pp.start(update, 295)
