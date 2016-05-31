import edevent
import edsmdb
import datetime

__all__ = [ 'NETLOG_LINE_TYPE', 'NETLOG_SHIP_STATUS', 'NETLOG_VERSION', 'NetlogLineFactory' ]

def _enum(**enums):
    return type('Enum', (), enums)

NETLOG_LINE_TYPE = _enum(INVALID = "Invalid",
                         SYSTEM = "System")

NETLOG_SHIP_STATUS = _enum(UNKNOWN = "unknown",
                           NORMAL_FLIGHT = "NormalFlight",
                           SUPERCRUISE = "Supercruise",
                           PROVING_GROUND = "ProvingGround")

NETLOG_VERSION = _enum(VERSION_2_0 = "<=2.0",
                       VERSION_2_1 = "2.1+")

class NetlogLineFactory():
    @staticmethod
    def get_line(line_time, line):
        parsed_line = _SystemLine.parse_netlog_line(line_time, line)
        
        return parsed_line

class _SystemLine(edevent.BaseEvent):
    def __init__(self,
                 version,
                 line_time,
                 system_name,
                 num_bodies = 0,
                 system_position = None,
                 position = (0.0, 0.0, 0.0),
                 ship_status = NETLOG_SHIP_STATUS.UNKNOWN):
        edevent.BaseEvent.__init__(self,NETLOG_LINE_TYPE.SYSTEM, line_time)

        self._version = version
        self._name = system_name
        self._num_bodies = num_bodies
        self._position = position
        self._ship_status = ship_status

        # Now that FD is supplying the system coordinates
        # we should look at pulling systems by cube/sphere
        # rather than by system name.        
        edsm_db = edsmdb.get_instance()
#         self._distances = edsm_db.get_distances(self._name, 120.0)
        self._distances = set()

        if system_position:
            self._system_coordinates = system_position
        else:            
            system = edsm_db.get_system(self._name)
            if system:
                self._system_coordinates = system.position
            else:
                self._system_coordinates = None

    @classmethod
    def parse_netlog_line(cls, line_time, line):
        if 'SystemName' in line:
            system = line['SystemName']
            
            if 'StarPos' in line:
                star_pos = tuple(float(f) for f in line['StarPos'].split(","))
                version = NETLOG_VERSION.VERSION_2_1
            else:
                star_pos = None
                version = NETLOG_VERSION.VERSION_2_0
            
            if 'Body' in line:
                body = int(line['Body'])
            else:
                body = 0
                
            if 'Pos' in line:
                pos = tuple(float(f) for f in line['Pos'].split(","))
            else:
                pos = (0.0, 0.0, 0.0)
                
            if 'TravelMode' in line:
                status = line['TravelMode']
                
                if status.startswith(str(NETLOG_SHIP_STATUS.NORMAL_FLIGHT)):
                    status = NETLOG_SHIP_STATUS.NORMAL_FLIGHT
                elif status.startswith(str(NETLOG_SHIP_STATUS.SUPERCRUISE)):
                    status = NETLOG_SHIP_STATUS.SUPERCRUISE
                elif status.startswith(str(NETLOG_SHIP_STATUS.PROVING_GROUND)):
                    status = NETLOG_SHIP_STATUS.PROVING_GROUND
                else:
                    status = NETLOG_SHIP_STATUS.UNKNOWN
                    
            return cls(version,
                       line_time,
                       system,
                       num_bodies = body,
                       system_position = star_pos,
                       position = pos,
                       ship_status = status)
        else:
            return None
            
    def _fill_json_dict(self, json_dict):
        json_dict['System'] = self._name
        json_dict['Bodies'] = self._num_bodies
        json_dict['Position'] = self._position
        json_dict['Status'] = self._ship_status
        
        if self._system_coordinates:
            json_dict['SystemCoord'] = self._system_coordinates
            
        if self._distances:
            dict_list = list()
            
            max_list_size = len(self._distances)
            if max_list_size > 10:
                max_list_size = 10
                
            for i in xrange(0, max_list_size):
                distance = self._distances[i]
                
                item = dict()
                item['name'] = distance.sys2.name
                item['distance'] = distance.distance
                
                if distance.sys2.position:
                    item['coords'] = distance.sys2.position
                
                dict_list.append(item)
                
            json_dict['Distances'] = dict_list

    def get_version(self):
        return self._version
    
    def get_name(self):
        return self._name

    def get_num_bodies(self):
        return self._num_bodies

    def get_position(self):
        return self._position

    def get_ship_status(self):
        return self._ship_status

    def get_system_coordinates(self):
        return self._system_coordinates
    
    def get_distances(self):
        return self._distances
    
    def __str__(self):
        return edevent.BaseEvent.__str__(self) + ", Name [" + self._name + "], Bodies [" + str(self._num_bodies) + "], Position [" + str(self._position) + "], Ship Status [" + self._ship_status + "]"

if __name__ == "__main__":
    system = _SystemLine(datetime.datetime.utcnow(), 'Prieluia ND-H b57-0', ship_status = NETLOG_SHIP_STATUS.SUPERCRUISE)
    print system.get_json()
