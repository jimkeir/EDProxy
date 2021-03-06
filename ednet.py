import socket, select
import json
import datetime
import struct
import logging
import sys, threading

import edconfig
from edconfig import EDConfig

import edevent
import ijpython
import wrapper
import tornado.websocket
import urllib

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
    def __init__(self, service_name, ipv4, port, http_port = 8097):
        super(EDDiscoveryMessageAnnounce, self).__init__(DISCOVERY_SERVICE_TYPE.ANNOUNCE, service_name)

        self.service_dict['Version'] = EDConfig.get_version()
        self.service_dict['ipv4'] = ipv4
        self.service_dict['port'] = port
        self.service_dict['http_port'] = http_port

    def get_ipv4(self):
        return self.service_dict['ipv4']

    def get_port(self):
        return self.service_dict['port']

    def get_http_port(self):
        return self.service_dict['http_port']
    
    def __str__(self):
        return "%s, IPv4 [%s], Port [%s]" % (super(EDDiscoveryMessageAnnounce, self).__str__(), self.get_ipv4(), str(self.get_port()))

class EDDiscoveryMessageQuery(EDDiscoveryMessageBase):
    def __init__(self, service_name = None):
        super(EDDiscoveryMessageQuery, self).__init__(DISCOVERY_SERVICE_TYPE.QUERY, service_name = service_name)

class EDDiscoveryService():
    def __init__(self, multicast_addr, multicast_port):
        self.log = logging.getLogger("com.fussyware.edproxy")
        
        self._multicast_addr = multicast_addr
        self._multicast_port = multicast_port

        self._event_queue = edevent.EDEventQueue()
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
            self._thread.daemon = True
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
            self.log.debug("Sending: [%s]", message)
            self._sock.sendto(message.get_json(), (self._multicast_addr, self._multicast_port))
            self._sock.sendto(message.get_json(), ('<broadcast>', self._multicast_port))
        except Exception:
            self.log.error("Failed sending data.", exc_info = sys.exc_info())
        
    def __run(self):
        group = socket.inet_aton(self._multicast_addr)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._sock.setblocking(0)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Multicast and WiFi are not friends, so set this up for a specific query-response broadcast too.
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Tell the OS about the multicast group membership.
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', edconfig.get_instance().get_discovery_ttl()))
        self._sock.bind(('', self._multicast_port))
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
                data, _ = self._sock.recvfrom(1024)

                if data:
                    try:
                        message = EDDiscoveryMessageFactory.get_message(json.loads(data))
                        
                        if (message.get_type() != DISCOVERY_SERVICE_TYPE.ANNOUNCE or message.get_name() != "edproxy"):
#                             self.log.debug("Received: [%s]", message)
                            self._event_queue.post(message)
                            self._event_queue.flush()
                    except:
                        pass
                else:
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
        self._initialized = False
        self._lock.release()

class EDProxyServer():
    def __init__(self, port):
        self.log = logging.getLogger("com.fussyware.edproxy")
        
        self._running = False
        self._initialized = False
        self._lock = threading.Lock()
        self._conditional = threading.Condition(self._lock)
        self._port = port
        self._event_queue = edevent.EDEventQueue()
        self._thread = None

    def add_listener(self, callback, *args, **kwargs):
        self._event_queue.add_listener(callback, *args, **kwargs)

    def start(self):
        if not self.is_running():
            self._lock.acquire()
            self._running = True

            self._thread = threading.Thread(target = self.__run)
            self._thread.daemon = True
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

        while self.is_running():
            try:
                rr, _, _ = select.select([sock], [], [], 0.5)
                if rr:
                    client, addr = sock.accept()
                    self._event_queue.post(EDProxyClient(client), addr)
            except Exception:
                self.log.error("Exception in server layer.", exc_info = sys.exc_info())
                self._lock.acquire()
                self._running = False
                self._lock.release()

        try:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except:
            pass

        self.log.info("Exiting proxy server listen thread.")
    
        self._lock.acquire()
        self._running = False
        self._initialized = False
        self._lock.release()

class PongEvent(edevent.BaseEvent):
    def __init__(self):
        edevent.BaseEvent.__init__(self, "Pong", datetime.datetime.now())
    
    def _fill_json_dict(self, json_dict):
        pass

class SendKeysEvent(edevent.BaseEvent):
    def __init__(self, json_dict):
        edevent.BaseEvent.__init__(self, "SendKeys", datetime.datetime.now())
        self._recv_data = json_dict['Keys']

    def _fill_json_dict(self, json_dict):
        json_dict['Keys'] = self._recv_data
    
    def get_keys(self):
        return self._recv_data
        
class StarMapGetDistancesEvent(edevent.BaseEvent):
    def __init__(self, json_dict, client):
        edevent.BaseEvent.__init__(self, "GetDistances", datetime.datetime.now())
        self._recv_data = json_dict['Distances']
        self._client = client

    def _fill_json_dict(self, json_dict):
        json_dict['Distances'] = self._recv_data
        
    def get_distances(self):
        return self._recv_data
    
    def get_proxy_client(self):
        return self._client
    
class StarMapDistanceResponseEvent(edevent.BaseEvent):
    def __init__(self):
        edevent.BaseEvent.__init__(self, "GetDistancesResult", datetime.datetime.now())
        
        self._distance_list = list()
    
    def add(self, sys1, sys2, distance):
        json_dict = dict()
        json_dict['sys1'] = sys1
        json_dict['sys2'] = sys2
        json_dict['distance'] = distance
        
        self._distance_list.append(json_dict)
        
    def _fill_json_dict(self, json_dict):
        if len(self._distance_list) > 0:
            json_dict['Distances'] = self._distance_list

class RecvNetEventFactory(object):
    @staticmethod
    def get_recv_event(json_dict, proxy_client = None):
        if json_dict['Type'] == 'SendKeys':
            return SendKeysEvent(json_dict)
        if json_dict['Type'] == 'GetDistances':
            return StarMapGetDistancesEvent(json_dict, proxy_client)
        else:
            return None
        
class EDProxyClient(object):
    def __init__(self, sock):
        self.log = logging.getLogger("com.fussyware.edproxy")
        
        self._running = True
        self._initialized = False

        self._lock = threading.Lock()
        self._conditional = threading.Condition(self._lock)
        
        self._register_list = list()
        self._start_time = None
        
        self._peername = sock.getpeername()
        self._wrapper = wrapper.SocketWrapper(sock)
        self._json_items = ijpython.JsonItems(self._wrapper)

        self._heartbeat = None
        self._heartbeat_event = threading.Event()
        
        self._event_queue = edevent.EDEventQueue()
        self._recv_event_queue = edevent.EDEventQueue()

        _thread = threading.Thread(target = self.__run)
        _thread.daemon = True
        _thread.start()

    def set_ondisconnect_listener(self, disconnect_listener):
        self._event_queue.add_listener(disconnect_listener)
        
    def set_onrecv_listener(self, recv_listener):
        self._recv_event_queue.add_listener(recv_listener)
        
    def get_peername(self):
        return self._peername
        
    def is_running(self):
        try:
            self._lock.acquire()
            return self._running
        finally:
            self._lock.release()

    def wait_for_initialized(self, timeout = None):
        if timeout and timeout < 0:
            timeout = None

        try:
            self._lock.acquire()
            if not self._initialized and self._running:
                self._conditional.wait(timeout)

                if not self._initialized and self._running:
                    raise TimeoutException("Timeout occurred waiting for initialization.")
        except:
            raise
        finally:
            self._lock.release()

    def is_initialized(self):
        try:
            self._lock.acquire()
            return self._initialized
        finally:
            self._lock.release()

    def get_start_time(self):
        return self._start_time

    def close(self):
        if self.is_running():
            try:
                self._lock.acquire()
                self._running = False
                self._heartbeat_event.set()
                self._wrapper.close()
            finally:
                self._lock.release()

    def send(self, event):
        if self.is_initialized() and self.is_running():
            _type = event.get_line_type()
            
            if _type in self._register_list:
                try:
                    self.log.debug(event.get_json())
                    self._wrapper.write(event.get_json())
                except socket.error as msg:
                    self.log.exception(msg)
                    self.close()
                except socket.timeout as msg:
                    self.log.exception(msg)
                    self.close()
        
    def __set_running(self, enabled):
        try:
            self._lock.acquire()
            self._running = enabled
        finally:
            self._lock.release()
            
    def __handle_init(self, json_map):
        self._register_list = json_map['Register']
        self._register_list.append("StarMapUpdated")
        self._register_list.append("GetDistances")
        self._register_list.append("GetDistancesResult")

        start_time = json_map['StartTime']

        if 'Heartbeat' in json_map:
            self._heartbeat = json_map['Heartbeat']
            if self._heartbeat != None and self._heartbeat > 0:
                self._heartbeat = self._heartbeat * 2
                self._register_list.append("Pong")
                
                _thread = threading.Thread(target = self.__heartbeat_run)
                _thread.daemon = True
                _thread.start()
            
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

        try:
            self._lock.acquire()
            self._initialized = True
            self._conditional.notify()
        finally:
            self._lock.release()

    def __handle_heartbeat(self, json_map):
        self._heartbeat_event.set()
    
    def __heartbeat_run(self):
        while self.is_running():
            if self._heartbeat_event.wait(self._heartbeat):
                if self.is_running():
#                 self.log.debug("Recieved a heartbeat message return pong.")
                    self.send(PongEvent())
            else:
                self.log.error("Two heartbeats were missed! Closing down the socket.")
                self.close()
                
            self._heartbeat_event.clear()
    
    def __run(self):
        while self.is_running():
            try:
                json_map = self._json_items.get_item()

                if 'Type' in json_map:
                    self.log.debug("Received message: [%s]" % str(json_map))
                    
                    if json_map['Type'] == 'Init':
                        self.__handle_init(json_map)
                    elif json_map['Type'] == 'Heartbeat':
                        self.__handle_heartbeat(json_map)
                    else:
                        event = RecvNetEventFactory.get_recv_event(json_map, self)
                        if event:
                            self.log.debug("Received [%s]" % str(event))
                            self._recv_event_queue.post(event)
            except Exception, e:
                self.log.exception(e)
                self.close()
                                        
        self.log.info("Exiting proxy client read thread.")
        
        self.close()
        self._event_queue.post(self)

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def initialize(self, websocket_server):
        tornado.websocket.WebSocketHandler.initialize(self)
        
        self._websocket_server = websocket_server
        
    def open(self, *args):
        self._log = logging.getLogger("com.fussyware.edproxy")

        self.stream.set_nodelay(True)        
        self._peername = self.stream.socket.getpeername() 
        
        self._heartbeat = None
        self._heartbeat_event = threading.Event()
        
        self._event_queue = edevent.EDEventQueue()
        self._recv_event_queue = edevent.EDEventQueue()

        self._register_list = list()
        self._start_time = None

        self._lock = threading.Lock()
        self._conditional = threading.Condition(self._lock)

        self._running = True
        self._initialized = False

        self._websocket_server._post(self, self._peername)
        

    def on_message(self, message):
        try:   
            json_map = json.loads(message)

            if 'Type' in json_map:
                if json_map['Type'] == 'Init':
                    self.__handle_init(json_map)
                else:
                    event = RecvNetEventFactory.get_recv_event(json_map, self)
                    if event:
                        self._log.debug("Received [%s]" % str(event))
                        self._recv_event_queue.post(event)
        except Exception, e:
            self._log.exception(e)
        
    def on_pong(self, data):
        self._heartbeat_event.set()
    
    def on_close(self):
        try:
            self._log.debug("Websocket is now closed.")
            self._lock.acquire()
            self._running = False
            self._event_queue.post(self)
        finally:
            self._lock.release()
        
    # Start of EDProxy custom routines
    def get_peername(self):
        return self._peername

    def set_ondisconnect_listener(self, disconnect_listener):
        self._event_queue.add_listener(disconnect_listener)
        
    def set_onrecv_listener(self, recv_listener):
        self._recv_event_queue.add_listener(recv_listener)
        
    def is_running(self):
        try:
            self._lock.acquire()
            return self._running
        finally:
            self._lock.release()

    def is_initialized(self):
        try:
            self._lock.acquire()
            return self._initialized
        finally:
            self._lock.release()

    def wait_for_initialized(self, timeout = None):
        if timeout and timeout < 0:
            timeout = None

        try:
            self._lock.acquire()
            if not self._initialized and self._running:
                self._conditional.wait(timeout)

                if not self._initialized and self._running:
                    raise TimeoutException("Timeout occurred waiting for initialization.")
        except:
            raise
        finally:
            self._lock.release()

    def get_start_time(self):
        return self._start_time

    def send(self, event):
        if self.is_initialized() and self.is_running():
            _type = event.get_line_type()
            
            if _type in self._register_list:
                try:
                    self._log.debug(event.get_json())
                    self.write_message(event.get_json())
                except:
                    self._log.error("Websocket was already closed on send.")

    def __heartbeat_run(self):
        if self.is_running():
            try:
                self.ping("ping")
                
                if self._heartbeat_event.wait(self._heartbeat * 2):
                    if self.is_running():
                        # Start the timer back up
                        self._heartbeat_timer = threading.Timer(self._heartbeat, self.__heartbeat_run)
                        self._heartbeat_timer.start()
                else:
                    self._log.error("Two heartbeats were missed! Closing down the socket.")
                    self.close()
                    
                self._heartbeat_event.clear()
            except:
                self._log.error("Websocket was already closed during ping")

    def __handle_init(self, json_map):
        self._register_list = json_map['Register']
        self._register_list.append("StarMapUpdated")
        self._register_list.append("GetDistances")
        self._register_list.append("GetDistancesResult")

        start_time = json_map['StartTime']

        if 'Heartbeat' in json_map:
            self._heartbeat = json_map['Heartbeat']
            if self._heartbeat != None and self._heartbeat > 0:
                self._heartbeat_timer = threading.Timer(self._heartbeat, self.__heartbeat_run)
                self._heartbeat_timer.start()
            
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

        try:
            self._lock.acquire()
            self._initialized = True
            self._conditional.notify()
        finally:
            self._lock.release()

class PictureWebHandler(tornado.web.StaticFileHandler):
    def parse_url_path(self, url_path):
        return tornado.web.StaticFileHandler.parse_url_path(self, urllib.unquote_plus(url_path))
    
class EDProxyWebServer(object):
    def __init__(self, port):
        self._log = logging.getLogger("com.fussyware.edproxy")
        
        self._port = port
        self._running = False

        self._lock = threading.Lock()

        self._event_queue = edevent.EDEventQueue()
        
    def add_listener(self, callback, *args, **kwargs):
        self._event_queue.add_listener(callback, *args, **kwargs)

    def start(self):
        if not self.is_running():
            self._lock.acquire()
            self._running = True

            self._thread = threading.Thread(target = self.__websocket_server_thread)
            self._thread.daemon = True
            self._thread.start()

            self._lock.release()

    def stop(self):
        if self.is_running():
            self._lock.acquire()
            self._running = False
            self._lock.release()

            tornado.ioloop.IOLoop.instance().stop()

            self._thread.join()

    def is_running(self):
        self._lock.acquire()
        ret = self._running
        self._lock.release()

        return ret
        
    def _post(self, websock, addr):
        self._event_queue.post(websock, addr)

    def __websocket_server_thread(self):
        image_path = edconfig.get_instance().get_image_path()
        print image_path
        settings = { "static_path": image_path }
        _app = tornado.web.Application([(r'/v1', WebSocketHandler, dict(websocket_server = self)),
                                        (r'/(.+\..+)', PictureWebHandler, dict(path=settings['static_path']))],
                                       **settings)
        _http_server = _app.listen(self._port)
                
        tornado.ioloop.IOLoop.instance().start()
        _http_server.stop()
