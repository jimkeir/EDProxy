import os
import datetime
import threading
import logging

import edutils

from netlogline import NetlogLineFactory
from edevent import EDEventQueue
import re
import edconfig
import edsmdb
from watchdog.events import RegexMatchingEventHandler
import time
from watchdog import observers

__all__ = [ 'parse_past_logs', 'EDNetlogMonitor' ]

def _get_log_files(path, logfile_prefix):
    if not path:
        raise ValueError("path is empty or None")

    netlog_list = list()

    path = os.path.join(os.path.abspath(path), "")

    _, _, filenames = os.walk(path).next()

    for f in filenames:
        if (f.startswith(logfile_prefix)):
            try:
                name = datetime.datetime.strptime(f.split(".")[1], "%y%m%d%H%M")
            except ValueError:
                name = datetime.datetime.strptime(f.split(".")[1], "%y%m%d%H%M%S")

            netlog_list.append((name, path + f))

        netlog_list = sorted(netlog_list, key = lambda x: x[0])

    return netlog_list

def _handle_regex_match(match, file_date, prev_time, start_time = None):
    line_groups = match.groupdict()
    
    line_time = _parse_date(line_groups['Time'])
    parsed_line = None

    if line_time:
        if prev_time and (line_time < prev_time):
            file_date += datetime.timedelta(days = 1)

        prev_time = line_time
        line_time = datetime.datetime.combine(file_date, line_time)
       
        if start_time:
            if (line_time >= start_time):
                parsed_line = NetlogLineFactory.get_line(line_time, line_groups)
        else:
            parsed_line = NetlogLineFactory.get_line(line_time, line_groups)
        
    return file_date, prev_time, parsed_line

def _parse_date(line):
    try:
        return datetime.datetime.strptime(line, "%H:%M:%S").time()
    except ValueError:
        # This is currently not a valid line. We will need to update this
        # if we plan to support the multi-line items.
        return None
    except:
        # There are times that the netlog files are either filled with 
        # binary data, or are corrupted. Either way we fall here.
        # Just ignore these lines and attempt to move on.
        return None

def parse_past_logs(netlog_path, netlog_prefix, callback, args = (), kwargs = {}, start_time = None):
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}

#         log = logging.getLogger("com.fussyware.edproxy")

    eq = EDEventQueue()
    eq.add_listener(callback, *args, **kwargs)

    regex_pre21 = re.compile(r'\{(?P<Time>\d+:\d+:\d+)\} System:(?P<SysTag>\d+)\((?P<SystemName>.+)\) Body:(?P<Body>\d+) Pos:\((?P<Pos>.+)\) (?P<TravelMode>\w+)')
    regex_post21 = re.compile(r'\{(?P<Time>\d+:\d+:\d+)\} System:\"(?P<SystemName>[^"]+)\" StarPos:\((?P<StarPos>[^)]+)\)ly (?:Body:(?P<Body>\d+) RelPos:\((?P<Pos>[^)]+)\)km )?(?P<TravelMode>\w+)')

    loglist = _get_log_files(netlog_path, netlog_prefix)

    if loglist:
        if start_time is None:
            file_date, _ = loglist[0]
            start_time = file_date

        for file_date, filename in loglist:
            file_date = file_date.date()

            if file_date >= start_time.date():
                logfile = open(filename, "r")

                prev_time = None
                for line in iter(logfile):
                    match = regex_post21.search(line)
                    if match:
                        file_date, prev_time, parsed_line = _handle_regex_match(match, file_date, prev_time, start_time)
                        
                        if parsed_line:
#                                 log.debug("We have parsed a new line into something: [%s]" % str(parsed_line))
                            eq.post(parsed_line)
                    else:
                        match = regex_pre21.search(line)
                        if match:
                            file_date, prev_time, parsed_line = _handle_regex_match(match, file_date, prev_time, start_time)
                            
                            if parsed_line:
#                                     log.debug("We have parsed a new line into something: [%s]" % str(parsed_line))
                                eq.post(parsed_line)

                logfile.close()
            
    eq.flush()

class EDNetlogMonitor(RegexMatchingEventHandler):
    def __init__(self, logfile_prefix = "netLog"):
        super(EDNetlogMonitor, self).__init__([ r".*%s\.\d+\.\d+\.log" % logfile_prefix ], [], True, False)
        
        self._log = logging.getLogger("com.fussyware.edproxy")

        # Python issue7980 bug workaround
        datetime.datetime.strptime('2012-01-01', '%Y-%m-%d')

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._running = False
        self._prefix = logfile_prefix
        self._event_queue = EDEventQueue()
        self._observer = None
        
        self._logfilename = None
        self._logfile = None
        
        self._regex_pre21 = re.compile(r'\{(?P<Time>\d+:\d+:\d+)\} System:(?P<SysTag>\d+)\((?P<SystemName>.+)\) Body:(?P<Body>\d+) Pos:\((?P<Pos>.+)\) (?P<TravelMode>\w+)')
        self._regex_post21 = re.compile(r'\{(?P<Time>\d+:\d+:\d+)\} System:\"(?P<SystemName>[^"]+)\" StarPos:\((?P<StarPos>[^)]+)\)ly (?:Body:(?P<Body>\d+) RelPos:\((?P<Pos>[^)]+)\)km )?(?P<TravelMode>\w+)')
    
    def start(self, netlog_path):
        with self._lock:
            if not self._running:
                if not netlog_path or len(netlog_path) == 0:
                    raise ValueError("Invalid path specified.")

                self._running = True
                
                loglist = _get_log_files(netlog_path, self._prefix)
                if loglist:
                    file_date, self._logfilename = loglist[-1]
                    self._date_created = file_date.date()
        
                    self._logfile = open(self._logfilename, "r")
                    self._logfile.seek(0, os.SEEK_END)
                    self._where= self._logfile.tell()
                    self._logfile.close()
                else:
                    self._logfilename = None
                    self._logfile = None
                    self._date_created = None
                    self._where = 0
                
                self._previous_time = None

                self._log.debug("Parsing [%s] [%s]" % (self._logfilename, str(self._date_created)))

                self._observer = observers.Observer()
                self._observer.schedule(self, netlog_path, False)
                self._observer.start()
                
                self._thread = threading.Thread(target = self.__file_modified_thread)
                self._thread.daemon = True
                self._thread.start()
    
    def stop(self):
        with self._lock:
            if self._running:
                self._running = False
                self._observer.stop()
                self._observer.join()
                self._observer = None
                
                self._stop_event.set()
                
                if self._logfilename:
                    self._logfilename = None
    
    def is_running(self):
        with self._lock:
            return self._running
    
    def add_listener(self, callback, *args, **kwargs):
        self._event_queue.add_listener(callback, *args, **kwargs)

    def set_netlog_prefix(self, value):
        self._prefix = value
#         self._regexes = [ re.compile(r".*%s\.\d+\.\d+\.log" % self._prefix, re.I) ]
        
    def get_netlog_prefix(self):
        return self._prefix
    
    def on_created(self, event):
        with self._lock:
            self._log.debug("New netLog file created: [%s]" % event.src_path)
            self._logfilename = event.src_path
                
            self._date_created = self.__get_logfile_date(event.src_path)
            self._previous_time = None
            self._where = 0
            
            self.__parse_log()
            
    def __file_modified_thread(self):
        while self.is_running():
            with self._lock:
                self.__parse_log()
                
                size = os.stat(self._logfilename)
            
            modified = False
            while self.is_running() and not modified:
                if size.st_size == os.stat(self._logfilename).st_size:
                    self._stop_event.wait(1.0)
                    self._stop_event.clear()
                else:
                    modified = True
                
    def __get_logfile_date(self, path):
        try:
            _, filename = os.path.split(path)
            
            date = datetime.datetime.strptime(filename.split(".")[1], "%y%m%d%H%M")
        except ValueError:
            date = datetime.datetime.strptime(filename.split(".")[1], "%y%m%d%H%M%S")
            
        return date.date()

    def __parse_log(self):
        try:
            self._logfile = open(self._logfilename, "r")
            self._logfile.seek(self._where)
            
            line = self._logfile.readline()
            
            while self._running and line:
#                 self._log.debug("Read in line from log: [%s]" % line)
                match = self._regex_post21.search(line)
                if match:
    #               self._log.debug("Read line is Post-2.1")
                    self._date_created, self._previous_time, parsed_line = _handle_regex_match(match, self._date_created, self._previous_time)
                     
                    if parsed_line:
    #                   self._log.debug("We have parsed a new line into something: [%s]" % str(parsed_line))
                        self._event_queue.post(parsed_line)
                else:
                    match = self._regex_pre21.search(line)
                    if match:
                        self._date_created, self._previous_time, parsed_line = _handle_regex_match(match, self._date_created, self._previous_time)
                         
                        if parsed_line:
                            self._event_queue.post(parsed_line)
                            
                self._where = self._logfile.tell()
                line = self._logfile.readline()
            
            self._logfile.close()
        except:
            self._log.exception("Failed reading from the logfile.")
        
def __log_parser(event):
#     print event
    pass
    
def _test_past_logs():
    import cProfile, pstats, StringIO
    pr = cProfile.Profile()
    pr.enable()

    parse_past_logs(edconfig.get_instance().get_netlog_path(),
                    "netLog",
                    __log_parser)
    
    pr.disable()
    s = StringIO.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    print s.getvalue()
    
def _test_parse_logs():
    monitor = EDNetlogMonitor()
    monitor.start("/Users/wes/src/pydev/edproxy/test")
    
    try:
        while True:
            time.sleep(1)
    except:
        monitor.stop()

if __name__ == "__main__":
    user_dir = os.path.join(edutils.get_user_dir(), ".edproxy")
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
 
    user_dir = os.path.join(user_dir, "edproxy.log")
    logging.basicConfig(format = "%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d    %(message)s", filename = user_dir)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    edsmdb.get_instance().connect()

#     _test_past_logs()
    _test_parse_logs()

#     while True:
#         print os.stat("D:\\Dropbox\\Weston Desktop\\Documents\\Elite Dangerous\\Logs\\netLog.160605111209.01.log")
#         time.sleep(1)