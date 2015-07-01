import os
import psutil
import socket

import xml.etree.ElementTree as ET

def get_ipaddr():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setblocking(0)
        s.connect(('8.8.8.8',80))
        ret = s.getsockname()[0]
        s.close()
    except:
        ret = socket.gethostbyname(socket.gethostname())

    return ret

def get_app_dir():
    return os.path.dirname(os.path.realpath(__file__))

def is_ed_running():
    for p in psutil.process_iter():
        try:
            pinfo = p.as_dict(attrs = ['pid', 'name'])
            if p.name().lower().startswith("elitedangerous"):
                return True
        except psutil.NoSuchProcess:
            pass

    return False

def is_verbose_enabled(path):
    tree = ET.parse(path)
    root = tree.getroot()

    network = root.find('Network')

    return ('VerboseLogging' in network.attrib) and (network.attrib['VerboseLogging'] == '1')

def set_verbose_enabled(path, enabled):
    tree = ET.parse(path)
    root = tree.getroot()

    network = root.find('Network')
    network.attrib['VerboseLogging'] = '1'

    tree.write(path)

def set_datestamp_enabled(path, enabled):
    tree = ET.parse(path)
    root = tree.getroot()

    network = root.find('Network')
    network.attrib['DatestampLog'] = '1'

    tree.write(path)

def get_logfile_prefix(path):
    tree = ET.parse(path)
    root = tree.getroot()

    network = root.find('Network')

    if 'LogFile' in network.attrib:
        prefix = network.attrib['LogFile']
    else:
        prefix = "netLog"

    return prefix

