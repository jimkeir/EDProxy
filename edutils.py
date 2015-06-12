import os
import psutil
import xml.etree.ElementTree as ET

def get_app_dir():
    return os.path.dirname(os.path.realpath(__file__))

def is_ed_running():
    for p in psutil.process_iter():
        if p.name().lower().startswith("elitedangerous"):
            return True

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

