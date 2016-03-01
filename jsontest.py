import os, sys
import json

import socket, select
import threading
import edsmdb
import time
import ijpython
import traceback
# import wrapper

class SocketWrapper(object):
    def __init__(self, sock):
        self._sock = sock
        self._sock.settimeout(60)
        
        self._lock = threading.Lock()        
        self._closed = False
        self._frame = False
        
    def close(self):
        if not self._closed:
            self._closed = True
            
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
    
            try:
                self._sock.close()
            except:
                pass
        
    def write(self, buf):
        try:
            self._lock.acquire()
            self._sock.sendall(buf)
        finally:
            self._lock.release()
            
    def read(self, bytes_read = 4096):
        if self._closed or bytes == 0:
            return ""
        
        try:
            rr = []
            while not rr and not self._closed:
                if self._frame:
                    rr, _, _ = select.select([self._sock], [], [], 0)
                    if not rr:
                        self._frame = False
                        return ""
                else:
                    rr, _, _ = select.select([self._sock], [], [], 2)
        except:
            self.close()
            
        if self._closed:
            return ""

        try:
            buf = self._sock.recv(bytes_read)
            
            if len(buf) < bytes_read:
                self._frame = True
                
            return buf 
        except socket.error as msg:
            print "error"
            self.close()
            return ""
        except socket.timeout as msg:
            print "timeout"
            return ""

class SocketServer(object):
    def __init__(self):
        self._thread = threading.Thread(target = self.__run)
        self._thread.start()
        self.closed = False
    
    def close(self):
        try:
            self.closed = True
            self.handle.close()
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
        except:
            pass

    def __run(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock = self._sock
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 42575))
        sock.listen(5)

        try:
            client, _ = sock.accept()
            
            self.handle = SocketWrapper(client)
            
            count = 0
#             for item in items(self.handle):
#                 print "Count", count, ":", item
#                 count= count + 1
#                 
#                 if self.closed:
#                     print 'we are closed?'
#                     break
                
            while not self.closed:
                try:
                    i = iter(ijpython.items(self.handle))
                    json_map = next(i)
                     
                    print "Count", count, ":", json_map
                    count = count + 1
                except Exception, e:
                    traceback.print_exc()
            
            print "what shutdown!?"
            self.handle.close()
        except Exception, e:
            print e
            print "Exception in server layer."
            
        try:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except:
            pass
        
try:
    edsm_db = edsmdb.get_instance()
    
    sol = edsm_db.get_system('Sol')
    sol_distances = edsm_db.get_distances('Sol')
    
    json_dict = dict()
    json_dict['Type'] = 'System'
    json_dict['System'] = 'Sol'
    json_dict['Bodies'] = 0
    json_dict['Position'] = (0, 0, 0)
    json_dict['Status'] = 'Supercruise'
    json_dict['SystemCoord'] = sol.position
    
    dict_list = list()
    for distance in sol_distances:
        item = dict()
        item['name'] = distance.sys2.name
        item['distance'] = distance.distance
        
        if distance.sys2.position:
            item['coords'] = distance.sys2.position
        
        dict_list.append(item)
        
    json_dict['Distances'] = dict_list
    
#     print "client [%s]" % json.dumps(json_dict)
    
    server = SocketServer()
    
    time.sleep(0.25)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.connect(("127.0.0.1", 42575))
    
    for i in range(10):
        sock.sendall(json.dumps(json_dict))
#         time.sleep(0.125)

    time.sleep(2)

    for i in range(10):
        sock.sendall(json.dumps(json_dict))
    
    try:
        time.sleep(5)
        server.close()
        
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
    except:
        pass
except KeyboardInterrupt:
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)
