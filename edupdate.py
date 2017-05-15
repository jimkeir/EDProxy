import threading
import urllib2
import logging
import urlparse
import os
import time
import tempfile
import shutil
import contextlib
import wx
import subprocess
from wx import wxEVT_CLOSE_WINDOW
import sys
import urllib
import re

UpgradeEventType = wx.NewEventType()
EVT_UPGRADE_EVENT = wx.PyEventBinder(UpgradeEventType, 1)

class UpgradeEvent(wx.PyCommandEvent):
    def __init__(self, updater):
        wx.PyCommandEvent.__init__(self, UpgradeEventType, wx.ID_ANY)
    
        self._updater = updater
        
    def get_updater(self):
        return self._updater
    
class EDUpdater(object):
    def __init__(self, parent, latest_url, version):
        self._log = logging.getLogger("com.fussyware.edproxy")
        self._log.setLevel(logging.DEBUG)
        
        self.parent = parent
        self.latest_url = latest_url
        self.version = version
        self._latest = ''
        
        self._lock = threading.Lock()
        self._conditional = threading.Event()
        self._running = True
        self._thread = threading.Thread(target = self.__run)
        self._thread.daemon = True
        self._thread.start()
        
    def is_running(self):
        self._lock.acquire()
        ret = self._running
        self._lock.release()
        
        return ret
    
    def stop(self):
        if self.is_running():
            self._lock.acquire()
            self._running = False
            self._conditional.set()
            self._lock.release()
            
            self._thread.join()
            
    def perform_update(self, latest):
        pass
    
    def __run(self):
        while self.is_running():
            try:
                with contextlib.closing(urllib2.urlopen(self.latest_url)) as response:
                    if response.getcode() == 200 or response.getcode() == None:
                        self._latest = response.read()
                        
                        if self._latest:
                            self._latest = self._latest.strip()
                            path = urlparse.urlparse(self._latest).path
                            path = os.path.basename(path)
                            
                            # Default to simply checking whether our assumed filename and the reported latest are identical:
                            upgradeAvailable = (path != self.version)

                            # Try to parse the incoming version string to be a bit smarter than a simple "not equal".
                            regex_versionCode = re.compile(r'.*?-.*?-(?P<Major>\d+).(?P<Minor>\d+).(?P<Build>\d+)?')
                            matchOurs = regex_versionCode.search(self.version)
                            matchTheirs = regex_versionCode.search(path)
                            if matchOurs and matchTheirs:
                                try:
                                    upgradeAvailable = (int(matchTheirs.group('Major')) > int(matchOurs.group('Major')))
                                    if not upgradeAvailable:
                                        upgradeAvailable = (int(matchTheirs.group('Minor')) > int(matchOurs.group('Minor')))
                                    if not upgradeAvailable and matchTheirs.group('Build') and matchOurs.group('Build'):
                                        upgradeAvailable = (int(matchTheirs.group('Build')) > int(matchOurs.group('Build')))
                                except Exception, e:
                                    self._log.error("Failed to parse version from [%s] and [%s] : %s", 
                                                    self.version, path, e)

                            if upgradeAvailable:
                                wx.PostEvent(self.parent, UpgradeEvent(self))
                    else:
                        self._log.error("Failed to get: [%s] with code [%d]", self.latest_url, response.getcode())

            except urllib2.URLError, e:
                self._log.error("Failed to get URL [%s]", e)
                
            # Wait for 12hrs
            self._conditional.wait(12 * 60 * 60)
            self._conditional.clear()
        
class EDWin32Updater(EDUpdater):
    def __init__(self, parent, version, base_url = "https://bitbucket.org/westokyo/edproxy/downloads"):
        filename = "edproxy-win32-" + version + ".exe"
        url = urlparse.urljoin(base_url, urlparse.urlparse(base_url).path + "/LATEST-win32")
        
        EDUpdater.__init__(self, parent, url, filename)
        
    def perform_update(self):
        try:
            tmpdir = tempfile.gettempdir()
            tmpdir = os.path.join(tmpdir, os.path.basename(self._latest))
            filename, _ = urllib.urlretrieve(self._latest, tmpdir)

            subprocess.Popen([filename], creationflags=0x00000008)
            wx.PostEvent(self.parent, wx.CloseEvent(wxEVT_CLOSE_WINDOW))

        except urllib2.URLError, e:
            self._log.error("Failed to get URL [%s]", e)

class EDMacOSXUpdater(EDUpdater):
    def __init__(self, parent, version, base_url = "https://bitbucket.org/westokyo/edproxy/downloads"):
        filename = "edproxy-macosx-" + version + ".dmg"
        url = urlparse.urljoin(base_url, urlparse.urlparse(base_url).path + "/LATEST-macosx")
        EDUpdater.__init__(self, parent, url, filename)
        
    def perform_update(self):
        tmpdir = tempfile.gettempdir()
        tmpdir = os.path.join(tmpdir, os.path.basename(self._latest))
        filename, _ = urllib.urlretrieve(self._latest, tmpdir)

        mnt_path = tempfile.mkdtemp("edproxy_update")
        
        # Mount the .dmg filesystem
        update_mount = ["/usr/bin/hdiutil", "attach", "-autoopen", "-mountpoint", mnt_path, filename]
        subprocess.Popen(update_mount)
        
        wx.PostEvent(self.parent, wx.CloseEvent(wxEVT_CLOSE_WINDOW))
        
if __name__ == "__main__":
    user_dir = os.path.expanduser("~") + "/src/pydev/edproxy/testbed"
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    logging.basicConfig(format = "%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d    %(message)s", filename = user_dir + "/edproxy.log")

    updater = EDWin32Updater("1.2.0")
    
    time.sleep(15)
    
    print "stopping updater"
    updater.stop()
    