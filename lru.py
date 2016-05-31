import collections

class LRU(object):
    def __init__(self, max_size = 50):
        self._key_map = {}
        self._hit_list = collections.Counter()
        self._max_size = max_size
    
    def get(self, key):
        try:
            ret = self._key_map[key]
            
            self._hit_list[key] += 1

            return ret
        except KeyError:
            return None

    def put(self, key, value):
        if not self._key_map.has_key(key):
            # We have a miss.
            if len(self._key_map) >= self._max_size:
                rm_key = self._hit_list.most_common()[-1][0]
            
                del self._hit_list[rm_key]
                del self._key_map[rm_key]
                
        self._key_map[key] = value            
        self._hit_list[key] += 1
        
        return value
            
    def clear(self):
        self._key_map.clear()
        self._hit_list.clear()
        
if __name__ == "__main__":
    lru = LRU(max_size=3)
    
    lru.put("red", "bob")
    lru.put("blue", "fred")
    lru.get("blue")
    lru.get("red")
    lru.get("red")
    lru.put("yellow", "don")
    lru.get("yellow")
    lru.get("yellow")
    lru.put("orange", "ron")
    
    
    lru.clear()
    