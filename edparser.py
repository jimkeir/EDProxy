import os
import datetime
import threading
import logging

import edutils

from netlogline import NetlogLineFactory
from edevent import EDEventQueue

__all__ = [ 'EDNetlogParser' ]

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

def _parse_date(line):
    try:
        line_time = line[0:len("{hh:mm:ss}")]
        line_time = datetime.datetime.strptime(line_time, "{%H:%M:%S}").time()

        line = line[len("{hh:mm:ss} "):]

        return (line_time, line)
    except ValueError:
        # This is currently not a valid line. We will need to update this
        # if we plan to support the multi-line items.
        return (None, None)
    except:
        # There are times that the netlog files are either filled with 
        # binary data, or are corrupted. Either way we fall here.
        # Just ignore these lines and attempt to move on.
        return (None, None)


class EDNetlogParser():
    def __init__(self, logfile_prefix = "netLog"):
        self.log = logging.getLogger("com.fussyware.edproxy")

        self._lock = threading.Lock()
        self._conditional = threading.Condition(self._lock)
        self._running = False
        self._prefix = logfile_prefix
        self._event_queue = EDEventQueue()

    def add_listener(self, callback, *args, **kwargs):
        self._event_queue.add_listener(callback, *args, **kwargs)

    def set_netlog_prefix(self, value):
        self._prefix = value
        
    def get_netlog_prefix(self):
        return self._prefix

    def is_running(self):
        self._lock.acquire()
        ret = self._running
        self._lock.release()

        return ret

    def start(self, netlog_path):
        if not self.is_running():
            if not netlog_path or len(netlog_path) == 0:
                raise ValueError("Invalid path specified.")

            self._lock.acquire()
            self._running = True
            _thread = threading.Thread(target = self.__run, args = (netlog_path,))
            _thread.daemon = True
            _thread.start()
            self._lock.release()

    def stop(self):
        if self.is_running():
            self._lock.acquire()
            self._running = False
            self._conditional.notify()
            self._lock.release()

    @staticmethod
    def parse_past_logs(netlog_path, netlog_prefix, callback, args = (), kwargs = {}, start_time = None):
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        eq = EDEventQueue()
        eq.add_listener(callback, *args, **kwargs)

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
                        line_time, line = _parse_date(line.rstrip())

                        if line and line_time:
                            if (prev_time is not None) and (line_time < prev_time):
                                file_date += datetime.timedelta(days = 1)

                            prev_time = line_time
                            line_time = datetime.datetime.combine(file_date, line_time)

                            if line_time >= start_time:
                                parsed_line = NetlogLineFactory.get_line(line_time, line)
                                if parsed_line is not None:
                                    eq.post(parsed_line)

                    logfile.close()
                
        eq.flush()

    def __run(self, netlog_path):
        while self.is_running():
            self._lock.acquire()
            while self._running and not edutils.is_ed_running():
                self._conditional.wait(2)
            self._lock.release()

            loglist = _get_log_files(netlog_path, self._prefix)
            if not loglist:
                raise ValueError("We already checked verbose logging yet no logs!")

            file_date, filename = loglist[-1]
            file_date = file_date.date()

            logfile = open(filename, "r")
            logfile.seek(0, os.SEEK_END)

            wait_time = 0.1
            prev_time = None

            while self.is_running() and edutils.is_ed_running():
                line = logfile.readline().rstrip()
                if not line:
                    self._lock.acquire()
                    self._conditional.wait(wait_time)
                    self._lock.release()

                    if wait_time < 2.0:
                        wait_time = wait_time + wait_time
                        if wait_time > 2.0:
                            wait_time = 2.0
                else:
                    wait_time = 0.1

                    line_time, line = _parse_date(line)
                    if line and line_time:
                        if (prev_time is not None) and (line_time < prev_time):
                            file_date += datetime.timedelta(days = 1)

                        prev_time = line_time
                        line_time = datetime.datetime.combine(file_date, line_time)

                        parsed_line = NetlogLineFactory.get_line(line_time, line)
                        if parsed_line is not None:
                            self._event_queue.post(parsed_line)

            logfile.close()

        self.log.info("Exiting netlog parser thread.")
        
        self._lock.acquire()
        self._running = False
        self._lock.release()
