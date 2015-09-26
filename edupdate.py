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

UpgradeEventType = wx.NewEventType()
EVT_UPGRADE_EVENT = wx.PyEventBinder(UpgradeEventType, 1)

class UpgradeEvent(wx.PyCommandEvent):
    def __init__(self, upgrade_file_path, updater):
        wx.PyCommandEvent.__init__(self, UpgradeEventType, wx.ID_ANY)
    
        self._upgrade_file_path = upgrade_file_path
        self._updater = updater
        
    def get_upgrade_file_path(self):
        return self._upgrade_file_path
    
    def get_updater(self):
        return self._updater
    
class EDUpdater(object):
    def __init__(self, parent, latest_url, version):
        self._log = logging.getLogger("com.fussyware.edproxy")
        self._log.setLevel(logging.DEBUG)
        
        self.parent = parent
        self.latest_url = latest_url
        self.version = version
        
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
                    print response.getcode()
                    if response.getcode() == 200 or response.getcode() == None:
                        latest = response.read()
                        
                        if latest:
                            latest = latest.strip()
                            path = urlparse.urlparse(latest).path
                            path = os.path.basename(path)
                            
                            if path != self.version:
                                tmpdir = tempfile.gettempdir()
                                tmpdir = os.path.join(tmpdir, path)
                                
                                with open(tmpdir, "w") as tmpfile:
                                    with contextlib.closing(urllib2.urlopen(latest)) as download:
                                        if download.getcode() == 200 or download.getcode() == None:
                                            shutil.copyfileobj(download, tmpfile)
                                            wx.PostEvent(self.parent, UpgradeEvent(tmpfile.name, self))
                                        else:
                                            self._log.error("Failed to get: [%s] with code [%d]", latest, response.getcode())                                    
                    else:
                        self._log.error("Failed to get: [%s] with code [%d]", self.latest_url, response.getcode())
            except urllib2.URLError, e:
                self._log.error("Failed to get URL [%s]", e)
                
            # Wait for 12hrs
            self._conditional.wait(12 * 60 * 60)
            self._conditional.clear()
        
class EDWin32Updater(EDUpdater):
    def __init__(self, parent, version, base_url = "https://bitbucket.org/westokyo/edproxy/downloads"):
        filename = "edproxy-" + version + ".zip"
        url = urlparse.urljoin(base_url,
                               os.path.join(urlparse.urlparse(base_url).path, "LATEST-win32"))
        
        EDUpdater.__init__(self, parent, url, filename)
        
    def perform_update(self, latest):
        print "Update win32:", latest
        subprocess.Popen([latest], creationflags=0x00000008, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        wx.PostEvent(self.parent, wx.CloseEvent(wxEVT_CLOSE_WINDOW))
        
class EDMacOSXUpdater(EDUpdater):
    def __init__(self, parent, version, base_url = "https://bitbucket.org/westokyo/edproxy/downloads"):
        filename = "edproxy-macosx-" + version + ".dmg"
        url = urlparse.urljoin(base_url,
                               os.path.join(urlparse.urlparse(base_url).path, "LATEST-macosx"))
        EDUpdater.__init__(self, parent, url, filename)
        
    def perform_update(self, latest):
        print "Update macosx:", latest
        
        mnt_path = tempfile.mkdtemp("edproxy_update")
        
        # Mount the .dmg filesystem
        update_mount = ["/usr/bin/hdiutil", "attach", "-autoopen", "-mountpoint", mnt_path, latest]
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
    