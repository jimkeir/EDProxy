#!/usr/bin/env python

import os, sys
import socket, select
import json
import datetime, time
import threading
import logging

import ednet
import ijson

class ProxyClient(object):
    def __init__(self, name = "", start_time = "now"):
        self.log = logging.getLogger("com.fussyware.edproxy_test");
        self.log.setLevel(logging.DEBUG)

        self._found = False
        self._running = True

        self._discovery_service = ednet.EDDiscoveryService("239.45.99.98", 45551)
        self._discovery_service.add_listener(self.__on_new_message)

        self._name = name
        self._start_time = start_time
        
        threading.Thread(target = self.__run).start()

    def is_running(self):
        return self._running

    def stop(self):
        self._running = False

#     def __get_json(self, sock, prev_data = None):
#         prev_data += sock.recv(1024)
#         if prev_data:
#             idx = prev_data.find('}')
# 
#             while idx is not -1:
#                 data = prev_data[:idx + 1]
#                 prev_data = prev_data[idx + 1:]
#                 idx = prev_data.find('}')
# 
#                 jmap = json.loads(data)
#                 
#                 self.log.debug("[%s] %s" % (self._name, jmap))
#                 
#         return prev_data
    
    def __get_json(self, sock, prev_data = None):
        return ijson.items(sock, 'item')
        
    def __on_new_message(self, message):
        if message.get_type() == ednet.DISCOVERY_SERVICE_TYPE.ANNOUNCE:
            if message.get_name() == "edproxy" and not self._found:
                print "New Announcement: ", message
                self._ipaddr = message.get_ipv4()
                self._port = message.get_port()
                self._found = True

    def __run(self):
        while self._running:
            print "Start search for Edproxy..."
#             self._discovery_service.start()
#             self._discovery_service.send(ednet.EDDiscoveryMessageQuery('edproxy'))
#             while not self._found:
#                 print "Waiting on EDProxy..."
#                 time.sleep(2)
#                 self._discovery_service.send(ednet.EDDiscoveryMessageQuery('edproxy'))
#             self._discovery_service.stop()

            self._found = True
            self._ipaddr = "10.2.11.59"
#             self._ipaddr = "192.168.1.136"
            self._port = 45550
            
            print "[%s] Found EDProxy at: %s:%s" % (self._name, self._ipaddr, str(self._port))

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.connect((self._ipaddr, int(self._port)))

                json_init = json.dumps({ 'Date': datetime.datetime.now().isoformat(),
                                         'Type': "Init",
                                         # 'StartTime': "2015-05-31T11:45:23",
                                         'StartTime': self._start_time,
                                         'Register': [ "System" ] })

                self.log.debug("[%s] %s" % (self._name, json_init))
                print ("[%s] %s" % (self._name, json_init))
                    
                sock.sendall(json_init)
            except Exception, e:
                print "Failed connecting to EDProxy: ", e
                self._found = False

            print "[%s] Finished connection..." % self._name
            value = ""
            while self._running and self._found:
                try:
                    rr, _, _ = select.select([sock], [], [], 2)

                    if rr:
#                         value = self.__get_json(sock, value)
                        for item in self.__get_json(sock.makefile()):
                            print item
                except Exception, e:
                    print "Socket received error: ", e
                    self._found = False
            
            print "[%s] Finished with this connection of Edproxy." % self._name

            try:
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
            except:
                pass

        self._running = False

def edproxy_main():
    try:
        ed = ProxyClient(start_time="all")
        
        while ed.is_running():
            time.sleep(2)
        ed.stop()
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception, e:
        print "Failed starting up main. ", e
        sys.exit(0)

def edproxy_stress_test():
    client_list = list()
    
    try:
        for i in xrange(0, 1):
            client_list.append(ProxyClient(name=str(i), start_time="all"))
            time.sleep(0.250)
    
        for item in client_list:    
            while item.is_running():
                time.sleep(2)
            item.stop()
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception, e:
        print "Failed starting up main. ", e
        sys.exit(0)
    
def edproxy_discovery_announce():
    def _on_new_message(message, discovery):
        if message.get_type() == ednet.DISCOVERY_SERVICE_TYPE.QUERY:
            if not message.get_name() or message.get_name() == 'edproxy':
                discovery.send(ednet.EDDiscoveryMessageAnnounce('edproxy', "192.168.1.73", 45550))

    try:
        discovery = ednet.EDDiscoveryService("239.45.99.98", 45551)
        discovery.add_listener(_on_new_message, args = (discovery,))
        discovery.start()

        while discovery.is_running():
            time.sleep(2)

        discovery.stop()
    except KeyboardInterrupt:
        discovery.stop()

        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception, e:
        print "Error Announce: ", e
        sys.exit(0)

def edproxy_discovery_query():
    def _on_new_message(message, discovery):
        if message.get_type() == ednet.DISCOVERY_SERVICE_TYPE.ANNOUNCE:
            print "Announced: ", message.get_json()

    try:
        discovery = ednet.EDDiscoveryService("239.45.99.98", 45551)
        discovery.add_listener(_on_new_message, args = (discovery,))
        discovery.start()

        discovery.send(ednet.EDDiscoveryMessageQuery('edproxy'))
        while discovery.is_running():
            time.sleep(2)

        discovery.stop()
    except KeyboardInterrupt:
        discovery.stop()

        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception, e:
        print "Error Query: ", e
        sys.exit(0)

try:
    logging.basicConfig(format = "%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d    %(message)s", filename = "./test/client_test.log")

    if sys.argv[1] == "main":
        edproxy_main()
    elif sys.argv[1] == "stress":
        edproxy_stress_test()
    elif sys.argv[1] == "announce":
        edproxy_discovery_announce()
    elif sys.argv[1] == "query":
        edproxy_discovery_query()
except KeyboardInterrupt:
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)
