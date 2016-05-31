from watchdog import observers
from watchdog.events import PatternMatchingEventHandler
import logging
from edevent import EDEventQueue
import threading
import os
import sys
import time
from datetime import datetime
import edutils
import PIL.Image
import urllib
import edparser
import edconfig
import netlogline
import edevent

_http_root_paths = []

def _enum(**enums):
    return type('Enum', (), enums)

IMAGE_CONVERT_FORMAT = _enum(BMP = ".bmp", PNG = ".png", JPG = ".jpg")

class _EDPictureEvent(edevent.BaseEvent):
    def __init__(self, url):
        edevent.BaseEvent.__init__(self, "Image", datetime.now())
        
        self.url = url
        
    def get_url(self):
        return self.url
    
    def __str__(self, *args, **kwargs):
        return str(self.url)

    def _fill_json_dict(self, json_dict):
        json_dict['ImageUrl'] = self.url
    
class EDPictureMonitor(PatternMatchingEventHandler):
    def __init__(self, path = ''):
        PatternMatchingEventHandler.__init__(self, patterns = [ "*.bmp" ], ignore_directories = True)

        self._path = path    
        
        if len(path) > 0:    
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

    def is_started(self):
        return (self._observer != None)
    
    def set_convert_format(self, image_format):
        self._convert_format = image_format
        
    def set_delete_after_convert(self, delete_file):
        self._delete_file = delete_file
        
    def set_name_replacement(self, name):
        if name:
            # Make sure we have a valid filename.
            name = name.translate(None, '~#%&*{}\:<>?/+|"')

        if name:
            self._name_replacement = name
        else:
            self._name_replacement = None
        
    def set_convert_space(self, value):
        if len(value) == 0:
            self._convert_space = None
        else:
            self._convert_space = value
        
    def set_image_path(self, path):
        self._path = path

        if len(path) > 0 and not path in _http_root_paths:    
            _http_root_paths.append(path)
        
    def get_convert_format(self):
        return self._convert_format
    
    def get_delete_after_convert(self):
        return self._delete_file
    
    def get_convert_space(self):
        return self._convert_space
    
    def get_name_replacement(self):
        return self._name_replacement
    
    def on_created(self, event):
        _thread = threading.Thread(target = self.__run_imaged, args = (event,))
        _thread.daemon = True
        _thread.start()        

    def __log_parser(self, event):
        if event.get_line_type() == netlogline.NETLOG_LINE_TYPE.SYSTEM:
            self._name_replacement = event.get_name()

        
    def start(self):
        if not self._observer:
            self._observer = observers.Observer()
            self._observer.schedule(self, self._path, False)
    
            self._url = "http://%s:%d/" % (edutils.get_ipaddr(), 8097)

            self._thread = threading.Thread(target = self.__run_httpd)
            self._thread.daemon = True
            self._thread.start()
        
    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        
    def __wait_for_finish(self, path):
        copying = True
        prev_size = 0
        
        while copying:
            size = os.path.getsize(path)
            
            if (size != prev_size):
                prev_size = size
                time.sleep(2)
            else:
                copying = False
                
    def __run_imaged(self, events):
        self.log.debug("New image created. Process...")
        pathname, filename = os.path.split(events.src_path)
        
        if self._convert_format != IMAGE_CONVERT_FORMAT.BMP:
            output_filename = ""
            
            if self._name_replacement:
                output_filename = "%s_%s%s" % (self._name_replacement, datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), self._convert_format)
            else:
                output_filename = os.path.splitext(filename)[0] + self._convert_format                
                
            if self._convert_space:
                output_filename = output_filename.replace(" ", self._convert_space)

            filename = output_filename
            
        converted = False
        convert_attempts = 1
        
        while not converted and convert_attempts != 5:
            self.log.debug("Image Conversion attempt: [%d]", convert_attempts)
            convert_attempts = convert_attempts + 1
            
            self.__wait_for_finish(events.src_path)
            
            try:
                if self._convert_format == IMAGE_CONVERT_FORMAT.BMP:
                    converted = True
                else:
                    PIL.Image.open(events.src_path).save(os.path.join(pathname, filename))
                    converted = True
                    
                    if (self._delete_file):
                        os.remove(events.src_path)
            except Exception as e:
                self.log.error("Failed converting image! [%s]", e)
        
        self.log.debug("Check to see if we converted.")
        if converted:
            self.log.debug("Yep, we converted so send the event.")
            self._event_queue.post(_EDPictureEvent(self._url + urllib.quote_plus(filename)))
    
        self.log.debug("Finished handling new image.")
        
    def __run_httpd(self):
        if not self._name_replacement:
            config_path, _ = os.path.split(os.path.normpath(edconfig.get_instance().get_netlog_path()))
            config_path = os.path.join(config_path, "AppConfig.xml")

            edparser.parse_past_logs(edconfig.get_instance().get_netlog_path(),
                                     edutils.get_logfile_prefix(config_path),
                                     self.__log_parser)
            edconfig.get_instance().set_image_name_replacement(self._name_replacement)
            
        try:
            self._observer.start()
        except:
            pass
        
def __test_on_created(path):
    print "Got path: ", path
    
if __name__ == "__main__":
    name = "Sagittarius A*"
    
    print name.translate(None, '~#%&*{}\:<>?/+|"')
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

    