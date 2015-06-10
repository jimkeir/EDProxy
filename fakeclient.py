#!/usr/bin/python

import os, sys
import socket, select
import json
import datetime, time

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("127.0.0.1", 45550))


json_init = json.dumps({ 'Date': datetime.datetime.now().isoformat(),
                         'Type': "Init",
                         'StartTime': "2015-05-31T11:45:23",
                         # 'StartTime': "all",
                         # 'StartTime': "now",
                         'Register': [ "System" ] })

print json_init
sock.sendall(json_init)

value = ""
while True:
    try:
        rr, _, _ = select.select([sock], [], [], 2)
        if rr:
            value += sock.recv(1024)
            if value:
                idx = value.find('}')

                while idx is not -1:
                    data = value[:idx + 1]
                    # print "data:", data
                    value = value[idx + 1:]
                    # print "value:", value
                    idx = value.find('}')

                    jmap = json.loads(data)
                    print jmap
    except KeyboardInterrupt:
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception, e:
        print e
        print "xxx:" + value + ":yyy:" + str(len(value))
        sys.exit(0)

