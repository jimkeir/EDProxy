from watchdog import observers
from watchdog.events import PatternMatchingEventHandler
import logging
from edevent import EDEventQueue
import threading
from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn
from SimpleHTTPServer import SimpleHTTPRequestHandler
import os
import sys
import time
from datetime import datetime
import json
import edutils
import PIL.Image
import urllib

_http_root_paths = []

def _enum(**enums):
    return type('Enum', (), enums)

IMAGE_CONVERT_FORMAT = _enum(BMP = ".bmp", PNG = ".png", JPG = ".jpg")

class _EDPictureEvent(object):
    def __init__(self, url):
        self.url = url
        self._time = datetime.now()
        self._time_utc = datetime.utcnow()
        
    def get_url(self):
        return self.url
    
    def __str__(self, *args, **kwargs):
        return str(self.url)

    def _get_json_header(self):
        ret = dict()
        
        ret['Date'] = self._time.strftime('%Y-%m-%d %H:%M:%S')
        ret['DateUtc'] = self._time_utc
        ret['Type'] = 'Image'

        return ret

    def get_json(self):
        value = self._get_json_header()
        value['ImageUrl'] = self.url
        
        return json.dumps(value)
    
class EDPictureDirHTTPRequestHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        for _path in _http_root_paths:
            _path = _path + "/" + path
            if (os.path.exists(_path)):
                return _path
            
        return SimpleHTTPRequestHandler.translate_path(self, path)
    
class _ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """ Handle requests for HTTP server in a thread."""

class EDPictureMonitor(PatternMatchingEventHandler):
    def __init__(self, path):
        PatternMatchingEventHandler.__init__(self, patterns = [ "*.bmp" ], ignore_directories = True)

        self._path = path        
        _http_root_paths.append(path)
        
        self.log = logging.getLogger("com.fussyware.edproxy")
        self.log.setLevel(logging.DEBUG)

        self._name_replacement = None
        self._convert_format = IMAGE_CONVERT_FORMAT.BMP
        self._delete_file = False
        self._convert_space = None
        
        self._event_queue = EDEventQueue()
        self._observer = None

    def add_listener(self, callback, *args, **kwargs):
        self._event_queue.add_listener(callback, *args, **kwargs)

    def set_convert_format(self, image_format):
        self._convert_format = image_format
        
    def set_delete_after_convert(self, delete_file):
        self._delete_file = delete_file
        
    def set_name_replacement(self, name):
        if len(name) == 0:
            self._name_replacement = None
        else:
            self._name_replacement = name
        
    def set_convert_space(self, value):
        if len(value) == 0:
            self._convert_space = None
        else:
            self._convert_space = value
        
    def set_image_path(self, path):
        self._path = path
        
    def get_convert_format(self):
        return self._convert_format
    
    def get_delete_after_convert(self):
        return self._delete_file
    
    def get_convert_space(self):
        return self._convert_space
    
    def get_name_replacement(self):
        return self._name_replacement
    
    def on_created(self, event):
        threading.Thread(target = self.__run_imaged, args = (event,)).start()        

    def start(self):
        if not self._observer:
            self._observer = observers.Observer()
            self._observer.schedule(self, self._path, False)
            self._observer.start()
    
            self._url = "http://%s:%d/" % (edutils.get_ipaddr(), 8097)

            self._http_server = _ThreadedHTTPServer(("", 8097), EDPictureDirHTTPRequestHandler)
            self._thread = threading.Thread(target = self.__run_httpd)
            self._thread.start()
        
    def stop(self):
        if self._observer:
            self._http_server.server_close()
            self._observer.stop()
            self._observer = None
        
    def __run_imaged(self, events):
        pathname, filename = os.path.split(events.src_path)
        
        if self._convert_format != IMAGE_CONVERT_FORMAT.BMP:
            output_filename = ""
            
            if self._name_replacement:
                output_filename = "%s_%s%s" % (self._name_replacement, datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), self._convert_format)
            else:
                output_filename = os.path.splitext(filename)[0] + self._convert_format                
                
            if self._convert_space:
                output_filename = output_filename.replace(" ", self._convert_space)
            
            PIL.Image.open(events.src_path).save(pathname + "/" + output_filename)

            if (self._delete_file):
                os.remove(events.src_path)
                
            filename = output_filename
        
        self._event_queue.post(_EDPictureEvent(self._url + urllib.quote_plus(filename)))
        
    
    def __run_httpd(self):
        try:
            self._http_server.serve_forever()
        except:
            pass
        
        self.log.info("Exiting httpd thread.")
        
def __test_on_created(path):
    print "Got path: ", path
    
if __name__ == "__main__":
    user_dir = os.path.expanduser("~") + "/src/pydev/edproxy/testbed"
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    logging.basicConfig(format = "%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d    %(message)s", filename = user_dir + "/edproxy.log")
    edmonitor = EDPictureMonitor(os.path.expanduser(sys.argv[1]))
    edmonitor.add_listener(__test_on_created)
    edmonitor.set_convert_format(IMAGE_CONVERT_FORMAT.PNG)
    edmonitor.set_delete_after_convert(True)
    edmonitor.set_name_replacement("This is TEST")
#     edmonitor.set_convert_space("_")
    edmonitor.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        edmonitor.stop()

    