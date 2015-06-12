import os
import datetime, time
import threading

import edutils

from netlogline import *

__all__ = [ 'EDNetlogParser' ]

def _get_log_files(path, logfile_prefix):
    if not path:
        raise ValueError("path is empty or None")

    netlog_list = list()

    path = os.path.join(os.path.abspath(path), "")

    _, _, filenames = os.walk(path).next()

    for f in filenames:
        if (f.startswith(logfile_prefix)):
            name = datetime.datetime.strptime(f.split(".")[1], "%y%m%d%H%M")

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
        self._lock = threading.Lock()
        self._running = False
        self._listener_list = list()
        self._prefix = logfile_prefix

    def add_listener(self, callback, args = (), kwargs = {}):
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        self._lock.acquire()
        self._listener_list.append((callback, args, kwargs))
        self._lock.release()

    def get_netlog_prefix(self):
        return self._prefix

    def is_running(self):
        self._lock.acquire()
        ret = self._running
        self._lock.release()

        return ret

    def start(self, netlog_path):
        if not self.is_running():
            if not netlog_path:
                raise ValueError("Invalid path specified.")

            self._lock.acquire()
            self._running = True
            threading.Thread(target = self.__run, args = (netlog_path,)).start()
            self._lock.release()

    def stop(self):
        if self.is_running():
            self._lock.acquire()
            self._running = False
            self._lock.release()

    @staticmethod
    def parse_past_logs(netlog_path, netlog_prefix, callback, args = (), kwargs = {}, start_time = None):
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
                                    if args is None:
                                        args = ()
                                    if kwargs is None:
                                        kwargs = {}

                                    newargs = (parsed_line,) + args
                                    callback(*newargs, **kwargs)

                    logfile.close()

    def __run(self, netlog_path):
        while self.is_running():
            while self.is_running() and not edutils.is_ed_running():
                time.sleep(2)

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
                    time.sleep(wait_time)

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
                            self._lock.acquire()
                            for callback, _args, _kwargs in self._listener_list:
                                newargs = (parsed_line,) + _args
                                callback(*newargs, **_kwargs)
                            self._lock.release()

            logfile.close()

        self._lock.acquire()
        self._running = False
        self._lock.release()
