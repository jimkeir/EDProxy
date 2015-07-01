import socket, select
import json
import datetime
import threading
import struct

from Queue import Queue, Empty

from edevent import *
from edparser import *
from netlogline import *

#class EDServiceBase():
#

def _enum(**enums):
    return type('Enum', (), enums)

DISCOVERY_SERVICE_TYPE = _enum(QUERY = "Query", ANNOUNCE = "Announce")

class TimeoutException(Exception):
    pass

class EDDiscoveryMessageFactory():
    @staticmethod
    def get_message(json_map):
        if json_map['type'] == DISCOVERY_SERVICE_TYPE.QUERY:
            if 'name' in json_map:
                service_name = json_map['name']
            else:
                service_name = None

            return EDDiscoveryMessageQuery(service_name = service_name)
        elif json_map['type'] == DISCOVERY_SERVICE_TYPE.ANNOUNCE:
            return EDDiscoveryMessageAnnounce(json_map['name'],
                                              json_map['ipv4'],
                                              json_map['port'])
        else:
            raise ValueError("Invalid message type specified.")
        
class EDDiscoveryMessageBase(object):
    def __init__(self, service_type, service_name = None):
        self.service_dict = dict()
        self.service_dict['type'] = service_type

        if service_name:
            self.service_dict['name'] = service_name
    def get_type(self):
        return self.service_dict['type']

    def get_name(self):
        if not 'name' in self.service_dict:
            return None
        else:
            return self.service_dict['name']

    def get_json(self):
        return json.dumps(self.service_dict)

    def __str__(self):
        return "Discovery Message: Type [%s], Name [%s]" % (self.get_type(), self.get_name())

class EDDiscoveryMessageAnnounce(EDDiscoveryMessageBase):
    def __init__(self, service_name, ipv4, port):
        super(EDDiscoveryMessageAnnounce, self).__init__(DISCOVERY_SERVICE_TYPE.ANNOUNCE, service_name)

        self.service_dict['ipv4'] = ipv4
        self.service_dict['port'] = port

    def get_ipv4(self):
        return self.service_dict['ipv4']

    def get_port(self):
        return self.service_dict['port']

    def __str__(self):
        return "%s, IPv4 [%s], Port [%s]" % (super(EDDiscoveryMessageAnnounce, self).__str__(), self.get_ipv4(), str(self.get_port()))

class EDDiscoveryMessageQuery(EDDiscoveryMessageBase):
    def __init__(self, service_name = None):
        super(EDDiscoveryMessageQuery, self).__init__(DISCOVERY_SERVICE_TYPE.QUERY, service_name = service_name)

class EDDiscoveryService():
    def __init__(self, broadcast_addr, broadcast_port):
        self._broadcast_addr = broadcast_addr
        self._broadcast_port = broadcast_port

        self._event_queue = EDEventQueue()
        self._lock = threading.Lock()
        self._conditional = threading.Condition(self._lock)
        self._running = False
        self._initialized = False
        self._thread = None

    def add_listener(self, callback, *args, **kwargs):
        self._event_queue.add_listener(callback, *args, **kwargs)

    def is_running(self):
        self._lock.acquire()
        ret = self._running
        self._lock.release()

        return ret

    def start(self):
        if not self.is_running():
            self._lock.acquire()
            self._running = True

            self._thread = threading.Thread(target = self.__run)
            self._thread.start()

            while self._running and not self._initialized:
                self._conditional.wait(1)
            self._lock.release()

    def stop(self):
        if self.is_running():
            self._lock.acquire()
            self._running = False
            self._lock.release()

            self._thread.join()

    def send(self, message):
        try:
            self._sock.sendto(message.get_json(), (self._broadcast_addr, self._broadcast_port))
        except Exception, e:
            print "Failed send: ", e
        
    def __run(self):
        group = socket.inet_aton(self._broadcast_addr)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(0)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
        self._sock.bind(('', self._broadcast_port))
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        self._lock.acquire()
        self._initialized = True
        self._conditional.notify()
        self._lock.release()

        while self.is_running():
            try:
                rr, _, _ = select.select([self._sock], [], [], 0.5)
            except:
                self._lock.acquire()
                self._running = False
                self._lock.release()

                rr = None

            if rr:
                data, address = self._sock.recvfrom(1024)

                if data:
                    try:
                        message = EDDiscoveryMessageFactory.get_message(json.loads(data))
                        self._event_queue.post(message)
                    except:
                        pass
                else:
                    self._lock.acquire()
                    self._running = False
                    self._lock.release()

        try:
            self._sock.shutdown(socket.RDRW)
            self._sock.close()
        except:
            pass

        self._lock.acquire()
        self._running = False
        self._initialized = False
        self._lock.release()

class EDProxyServer():
    def __init__(self, port):
        self._running = False
        self._initialized = False
        self._lock = threading.Lock()
        self._conditional = threading.Condition(self._lock)
        self._port = port
        self._event_queue = EDEventQueue()
        self._thread = None

    def add_listener(self, callback, *args, **kwargs):
        self._event_queue.add_listener(callback, *args, **kwargs)

    def start(self):
        if not self.is_running():
            self._lock.acquire()
            self._running = True

            self._thread = threading.Thread(target = self.__run)
            self._thread.start()

            while not self._initialized and self._running:
                try: self._conditional.wait(2)
                except: pass

            self._lock.release()

    def stop(self):
        if self.is_running():
            self._lock.acquire()
            self._running = False
            self._initialized = False
            self._lock.release()

            self._thread.join()

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

        self._lock.acquire()
        self._initialized = True
        self._conditional.notify()
        self._lock.release()

        client_list = list()
        while self.is_running():
            try:
                rr, _, _ = select.select([sock], [], [], 0.5)
                if rr:
                    client, addr = sock.accept()
                    self._event_queue.post(EDProxyClient(client), addr)
            except Exception, e:
                print "Exception in server layer.", e
                self._lock.acquire()
                self._running = False
                self._lock.release()

        try:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except:
            pass

        self._lock.acquire()
        self._running = False
        self._initialized = False
        self._lock.release()

class EDProxyClient():
    def __init__(self, sock):
        self._running = True
        self._initialized = False

        self._lock = threading.Lock()
        self._conditional = threading.Condition(self._lock)
        self._queue = Queue()
        self._register_list = list()
        self._start_time = None
        self._sock = sock

        threading.Thread(target = self.__run).start()

    def is_running(self):
        self._lock.acquire()
        ret = self._running
        self._lock.release()

        return ret

    def wait_for_initialized(self, timeout = None):
        if timeout and timeout < 0:
            timeout = None

        self._lock.acquire()
        try:
            if not self._initialized and self._running:
                self._conditional.wait(timeout)

                if not self._initialized and self._running:
                    raise TimeoutException("Timeout occurred waiting for initialization.")
        except:
            raise
        finally:
            self._lock.release()

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
                rr, _, _ = select.select([self._sock], [], [], 0.5)
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
                        self._conditional.notify()
                        self._lock.release()

        while self.is_running():
            try:
                line = self._queue.get(block = True, timeout = 0.5)

                self._sock.send(line.get_json())
            except Empty:
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
