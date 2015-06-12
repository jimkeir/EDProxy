import socket, select
import json
import Queue
import datetime
import threading
import struct

from edparser import *
from netlogline import *

#class EDServiceBase():
#
   
class EDDiscoveryService():
    def __init__(self, addr, port):
        self._broadcast_addr = addr
        self._port = port
        self._lock = threading.Lock()
        self._running = False

    def is_running(self):
        self._lock.acquire()
        ret = self._running
        self._lock.release()

        return ret

    def start(self):
        if not self.is_running():
            self._lock.acquire()
            self._running = True
            threading.Thread(target = self.__run).start()
            self._lock.release()

    def stop(self):
        if self.is_running():
            self._lock.acquire()
            self._running = False
            self._lock.release()
            
    def __run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
        sock.bind(('', self._port))

        group = socket.inet_aton(self._broadcast_addr)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        while self.is_running():
            data, address = sock.recvfrom(1500)

            print data

class EDProxyServer():
    def __init__(self, port):
        self._running = False
        self._lock = threading.Lock()
        self._port = port
        self._listener_list = list()

    def add_listener(self, callback):
        self._lock.acquire()
        self._listener_list.append(callback)
        self._lock.release()

    def start(self):
        if not self.is_running():
            self._lock.acquire()
            self._running = True
            threading.Thread(target = self.__run).start()
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

    def __run(self):
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
                    
                    self._lock.acquire()
                    try:
                        for listener in self._listener_list:
                            listener(EDProxyClient(client), addr)
                    except:
                        raise
                    finally:
                        self._lock.release()
            except:
                self._lock.acquire()
                self._running = False
                self._lock.release()

        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

        self._lock.acquire()
        self._running = False
        self._lock.release()

class EDProxyClient():
    def __init__(self, sock):
        self._running = True
        self._initialized = False

        self._lock = threading.Lock()
        self._queue = Queue.Queue()
        self._register_list = list()
        self._start_time = None
        self._sock = sock

        threading.Thread(target = self.__run).start()

    def is_running(self):
        self._lock.acquire()
        ret = self._running
        self._lock.release()

        return ret

    def is_initialized(self):
        self._lock.acquire()
        ret = self._initialized
        self._lock.release()

        return ret

    def get_start_time(self):
        return self._start_time

    def close(self):
        if self.is_running():
            self._lock.acquire()
            self._running = False
            self._lock.release()

    def send(self, line):
        if self.is_initialized() and self.is_running():
            if line.get_line_type() in self._register_list:
                self._queue.put(line)

    def __run(self):
        while self.is_running() and not self.is_initialized():
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
                        self._register_list = json_map['Register']
                        start_time = json_map['StartTime']

                        if start_time == "all":
                            self._start_time = datetime.datetime.fromtimestamp(0)
                        elif start_time == "now":
                            self._start_time = None
                        else:
                            __date = start_time
                            try:
                                __date = __date[:__date.index(".")]
                            except ValueError:
                                pass

                            self._start_time = datetime.datetime.strptime(__date, "%Y-%m-%dT%H:%M:%S")

                        self._lock.acquire()
                        self._initialized = True
                        self._lock.release()

                        # if start_time != "now":
                        #     if start_time == "all":
                        #         start_time = None
                        #     else:
                        #         __date = start_time
                        #         try:
                        #             __date = __date[:__date.index(".")]
                        #         except ValueError:
                        #             pass

                        #         start_time = datetime.datetime.strptime(__date, "%Y-%m-%dT%H:%M:%S")

                        #     callbacks = dict()
                        #     for reg_type in register_list:
                        #         if reg_type == NETLOG_LINE_TYPE.SYSTEM:
                        #             callbacks[reg_type] = (self.__system_sync_listener,)

                        #     EDNetlogParser.parse_past_logs(self._netlog_path, self._netlog_parser.get_netlog_prefix(), callbacks, start_time = start_time)

                        # for reg_type in register_list:
                        #     if reg_type == NETLOG_LINE_TYPE.SYSTEM:
                        #         self._netlog_parser.add_listener(NETLOG_LINE_TYPE.SYSTEM,
                        #                                          self.__system_async_listener)

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
