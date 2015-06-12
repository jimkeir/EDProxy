#!/usr/bin/python

import os, sys
import socket, select
import json
import datetime, time
import threading

import ednet

class ProxyClient(object):
    def __init__(self):
        self._found = False
        self._running = True

        self._discovery_service = ednet.EDDiscoveryService("239.45.99.98", 45551)
        self._discovery_service.add_listener(self.__on_new_message)

        threading.Thread(target = self.__run).start()

    def is_running(self):
        return self._running

    def stop(self):
        self._running = False

    def __on_new_message(self, message):
        if message.get_type() == ednet.DISCOVERY_SERVICE_TYPE.ANNOUNCE:
            if message.get_name() == "edproxy" and not self._found:
                print "New Announcement: ", message
                self._ipaddr = message.get_ipv4()
                self._port = message.get_port()
                self._found = True

    def __run(self):
        while self._running:
            self._discovery_service.start()
            self._discovery_service.send(ednet.EDDiscoveryMessageQuery('edproxy'))
            while not self._found:
                print "Waiting on EDProxy..."
                time.sleep(2)
                self._discovery_service.send(ednet.EDDiscoveryMessageQuery('edproxy'))
            self._discovery_service.stop()

            print "Found EDProxy at: %s:%s" % (self._ipaddr, str(self._port))

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.connect((self._ipaddr, int(self._port)))

                json_init = json.dumps({ 'Date': datetime.datetime.now().isoformat(),
                                         'Type': "Init",
                                         # 'StartTime': "2015-05-31T11:45:23",
                                         # 'StartTime': "all",
                                         'StartTime': "now",
                                         'Register': [ "System" ] })

                print json_init
                sock.sendall(json_init)
            except Exception, e:
                print "Failed connecting to EDProxy: ", e
                self._found = False

            value = ""
            while self._running and self._found:
                try:
                    rr, _, _ = select.select([sock], [], [], 2)

                    if rr:
                        value += sock.recv(1024)
                        if not value:
                            self._found = False
                        else:
                            idx = value.find('}')

                            while idx is not -1:
                                data = value[:idx + 1]
                                value = value[idx + 1:]
                                idx = value.find('}')

                                jmap = json.loads(data)
                                print jmap
                except Exception, e:
                    print "Socket received error: ", e
                    self._found = False

            try:
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
            except:
                pass

        self._running = False

def edproxy_main():
    try:
        ed = ProxyClient()
        
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
    if sys.argv[1] == "main":
        edproxy_main()
    elif sys.argv[1] == "announce":
        edproxy_discovery_announce()
    elif sys.argv[1] == "query":
        edproxy_discovery_query()
except KeyboardInterrupt:
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)
