import socket, select
import json
import Queue
import datetime
import threading

from edparser import *
from netlogline import *

class EDProxyServer():
    def __init__(self, port, netlog_parser):
        self._running = False
        self._lock = threading.Lock()
        self._port = port
        self._netlog_parser = netlog_parser

    def start(self, netlog_path):
        if not self.is_running():
            self._lock.acquire()
            self._running = True
            threading.Thread(target = self.__run, args = (netlog_path,)).start()
            self._lock.release()

    def stop(self):
        if self.is_running():
            self._lock.acquire()
            self._running = False
            self._lock.release()

    def is_running(self):
        self._lock.acquire()
        ret = self._running
        self._lock.release()

        return ret

    def __run(self, netlog_path):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self._port))
        sock.listen(5)

        client_list = list()
        while self.is_running():
            try:
                rr, _, _ = select.select([sock], [], [], 2)
                if rr:
                    client, addr = sock.accept()

                    client_list.append(EDProxyClient(client, netlog_path, self._netlog_parser))
            except:
                self._lock.acquire()
                self._running = False
                self._lock.release()

        # Yes some data may be stale, or errored out.
        # Doesn't really matter. Their stop routine
        # will just harmless pass through. Ineffecient?
        # Yes. Unclean? Yes. Simple and straight forward
        # with little complexity. Yes.
        for client in client_list:
            client.stop()

        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

        self._lock.acquire()
        self._running = False
        self._lock.release()

class EDProxyClient():
    def __init__(self, sock, netlog_path, netlog_parser):
        self._running = True
        self._lock = threading.Lock()
        self._queue = Queue.Queue()
        self._sock = sock
        self._netlog_path = netlog_path
        self._netlog_parser = netlog_parser

        threading.Thread(target = self.__run).start()

    def is_running(self):
        self._lock.acquire()
        ret = self._running
        self._lock.release()

        return ret

    def stop(self):
        if self.is_running():
            self._lock.acquire()
            self._running = False
            self._lock.release()

    def __system_async_listener(self, line):
        self._queue.put(line)

    def __system_sync_listener(self, line):
        try:
            self._sock.send(line.get_json())
        except:
            self._lock.acquire()
            self._running = False
            self._lock.release()

    def __run(self):
        initialized = False

        while self.is_running() and not initialized:
            try:
                rr, _, _ = select.select([self._sock], [], [], 2)
            except:
                self._lock.acquire()
                self._running = False
                self._lock.release()
                
            if rr:
                json_map = None

                try:
                    json_map = self._sock.recv(1024)
                except:
                    self._lock.acquire()
                    self._running = False
                    self._lock.release()

                if json_map:
                    json_map = json.loads(json_map)
                    if json_map['Type'] == 'Init':
                        initialized = True

                        register_list = json_map['Register']
                        start_time = json_map['StartTime']

                        if start_time != "now":
                            if start_time == "all":
                                start_time = None
                            else:
                                __date = start_time
                                try:
                                    __date = __date[:__date.index(".")]
                                except ValueError:
                                    pass

                                start_time = datetime.datetime.strptime(__date, "%Y-%m-%dT%H:%M:%S")

                            callbacks = dict()
                            for reg_type in register_list:
                                if reg_type == NETLOG_LINE_TYPE.SYSTEM:
                                    callbacks[reg_type] = self.__system_sync_listener

                            EDNetlogParser.parse_past_logs(self._netlog_path, callbacks, start_time = start_time)

                        for reg_type in register_list:
                            if reg_type == NETLOG_LINE_TYPE.SYSTEM:
                                self._netlog_parser.add_listener(NETLOG_LINE_TYPE.SYSTEM,
                                                                 self.__system_async_listener)

        while self.is_running():
            try:
                line = self._queue.get(block = True, timeout = 2)
                self._sock.send(line.get_json())
            except Queue.Empty:
                pass
            except:
                self._lock.acquire()
                self._running = False
                self._lock.release()

        try:
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
        except:
            pass

        self._lock.acquire()
        self._running = False
        self._lock.release()
