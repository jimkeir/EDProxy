import socket, select
import threading
import logging

class SocketWrapper(object):
    def __init__(self, sock):
        self._log = logging.getLogger("com.fussyware.edproxy")

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
        if self._closed or bytes_read == 0:
            self._log.debug("closed [%s], bytes [%d]" % (str(self._closed), bytes_read))
            return ""
        
        try:
            rr = []
            while not rr and not self._closed:
                if self._frame:
                    rr, _, _ = select.select([self._sock], [], [], 0.250)
                    if not rr:
                        self._frame = False
                        self._log.debug("Framing is done so send blank")
                        return ""
                else:
                    rr, _, _ = select.select([self._sock], [], [], 2)
        except:
            self.close()
            
        if self._closed:
            self._log.debug("Socket has been closed")
            return ""

        try:
            buf = self._sock.recv(bytes_read)
            
            if len(buf) < bytes_read:
                self._frame = True
                
            return buf 
        except socket.error as msg:
            self.close()
            self._log.debug("Socket error")
            return ""
        except socket.timeout as msg:
            self._log.debug("Socket timeout")
            return ""
