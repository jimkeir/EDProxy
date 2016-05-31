import os
import psutil
import socket

import xml.etree.ElementTree as ET
import sys

def get_potential_log_dirs():
    home_dir = os.path.expanduser('~')
    potential_paths = list()

    if sys.platform == "win32":
        potential_paths.append(os.path.join(home_dir, "AppData\\Local\\Frontier_Developments\\Products\\elite-dangerous-64\\Logs"))
        potential_paths.append("C:\\Program Files (x86)\\Steam\\steamapps\\common\\Elite Dangerous\\Products\\elite-dangerous-64\\Log")
        potential_paths.append("C:\\Program Files (x86)\\Frontier\\Products\\elite-dangerous-64\\Logs")
        potential_paths.append("C:\\Program Files (x86)\\Frontier\\EDLaunch\\Products\\elite-dangerous-64\\Logs")

        potential_paths.append(os.path.join(home_dir, "AppData\\Local\\Frontier_Developments\\Products\\FORC-FDEV-D-1010\\Logs"))
        potential_paths.append("C:\\Program Files (x86)\\Steam\\steamapps\\common\\Elite Dangerous\\Products\\FORC-FDEV-D-1010\\Log")
        potential_paths.append("C:\\Program Files (x86)\\Frontier\\Products\\FORC-FDEV-D-1010\\Logs")
        potential_paths.append("C:\\Program Files (x86)\\Frontier\\EDLaunch\\Products\\FORC-FDEV-D-1010\\Logs")
    elif sys.platform == "darwin":
        potential_paths.append(os.path.join(home_dir, "Library/Application Support/Frontier Developments/Elite Dangerous/Logs"))
        potential_paths.append(os.path.join(home_dir, "Library/Application Support/Steam/steamapps/common/Elite Dangerous/Products/elite-dangerous-64/Logs"))
        potential_paths.append(os.path.join(home_dir, "Library/Application Support/Steam/steamapps/common/Elite Dangerous/Products/FORC-FDEV-D-1010/Logs"))

    return potential_paths

def get_potential_appconfig_dirs():
    home_dir = os.path.expanduser('~')
    potential_paths = list()

    if sys.platform == "win32":
        potential_paths.append(os.path.join(home_dir, "AppData\\Local\\Frontier_Developments\\Products\\elite-dangerous-64"))
        potential_paths.append("C:\\Program Files (x86)\\Steam\\steamapps\\common\\Elite Dangerous\\Products\\elite-dangerous-64")
        potential_paths.append("C:\\Program Files (x86)\\Frontier\\Products\\elite-dangerous-64")
        potential_paths.append("C:\\Program Files (x86)\\Frontier\\EDLaunch\\Products\\elite-dangerous-64")

        potential_paths.append(os.path.join(home_dir, "AppData\\Local\\Frontier_Developments\\Products\\FORC-FDEV-D-1010"))
        potential_paths.append("C:\\Program Files (x86)\\Steam\\steamapps\\common\\Elite Dangerous\\Products\\FORC-FDEV-D-1010")
        potential_paths.append("C:\\Program Files (x86)\\Frontier\\Products\\FORC-FDEV-D-1010")
        potential_paths.append("C:\\Program Files (x86)\\Frontier\\EDLaunch\\Products\\FORC-FDEV-D-1010")
    elif sys.platform == "darwin":
        potential_paths.append(os.path.join(home_dir, "Library/Application Support/Frontier_Developments/Products/elite-dangerous-64/EliteDangerous.app/Contents/Resources"))
        potential_paths.append(os.path.join(home_dir, "Library/Application Support/Frontier_Developments/Products/FORC-FDEV-D-1010/EliteDangerous.app/Contents/Resources"))
        potential_paths.append(os.path.join(home_dir, "Library/Application Support/Steam/steamapps/common/Elite Dangerous/Products/elite-dangerous-64/EliteDangerous.app/Contents/Resources"))
        potential_paths.append(os.path.join(home_dir, "Library/Application Support/Steam/steamapps/common/Elite Dangerous/Products/FORC-FDEV-D-1010/EliteDangerous.app/Contents/Resources"))

    return potential_paths

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

def get_user_dir():
    return os.path.expanduser("~")

def get_edproxy_dir():
    return os.path.join(get_user_dir(), ".edproxy")

def get_database_dir():
    return os.path.join(get_edproxy_dir(), "databases")

def is_ed_running():
#     return True
    for p in psutil.process_iter():
        try:
            pinfo = p.as_dict(attrs = ['pid', 'name'])
            if pinfo['name'] and pinfo['name'].lower().startswith("elitedangerous"):
                return True
        except psutil.NoSuchProcess:
            pass
 
    return False

def create_local_appconfig(path):
    contents = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<AppConfig>\n\t<Network Port=\"0\" upnpenabled=\"1\" LogFile=\"netLog\" VerboseLogging=\"1\" DatestampLog=\"1\" />\n</AppConfig>\n"
    
    fout = open(os.path.join(path, "AppConfigLocal.xml"), 'w')
    fout.write(contents)
    fout.close()
    
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

