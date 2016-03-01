import socket, select
import threading

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
            self.close()
            return ""
        except socket.timeout as msg:
            return ""
