import threading

from Queue import Queue
import time
import logging

class _EDThreadWorker(threading.Thread):
    def __init__(self, task_queue):
        self._log = logging.getLogger("com.fussyware.edproxy")

        super(_EDThreadWorker, self).__init__()

        self._task_queue = task_queue
        self.daemon = True

        self.start()

    def run(self):
        while True:
            try:
                func, args, kwargs = self._task_queue.get(block=True, timeout = 2)

                try: func(*args, **kwargs)
                except: pass

                self._task_queue.task_done()
            except:
                pass

class _EDThreadPool(object):
    def __init__(self, num_threads):
        self._log = logging.getLogger("com.fussyware.edproxy")
        self._task_queue = Queue()

        for _ in range(num_threads):
            _EDThreadWorker(self._task_queue)

    def add_task(self, func, *args, **kwargs):
        self._task_queue.put_nowait((func, args, kwargs))

_thread_pool = _EDThreadPool(1)
def _get_thread_pool():
    return _thread_pool

class EDEventQueue(object):
    def __init__(self):
        self._log = logging.getLogger("com.fussyware.edproxy")
        self._listener_list = list()
        self._event_list = list()
        self._lock = threading.Lock()
        self._pool = _get_thread_pool()

    def __event_worker(self, *args, **kwargs):
        try:
            self._lock.acquire()
            for listener, _args, _kwargs in self._listener_list:
                newargs = args + _args
                newkwargs = kwargs.copy()
                newkwargs.update(_kwargs)
    
                listener(*newargs, **newkwargs)
                
            self._event_list.remove(args)
        finally:
            self._lock.release()

    def add_listener(self, func, *args, **kwargs):
        try:
            self._lock.acquire()
            self._listener_list.append((func, args, kwargs))
        finally:
            self._lock.release()

    def post(self, *args, **kwargs):
        try:
            self._lock.acquire()
            self._event_list.append(args)
        finally:
            self._lock.release()
        
        self._pool.add_task(self.__event_worker, *args, **kwargs)

    def size(self):
        try:
            self._lock.acquire()
            return len(self._event_list)
        finally:
            self._lock.release()
    
    def flush(self):
        while self.size() != 0:
            time.sleep(0.120)
            