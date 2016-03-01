import json
import edevent
import edsmdb
import datetime

__all__ = [ 'NETLOG_LINE_TYPE', 'NETLOG_SHIP_STATUS', 'NetlogLineFactory' ]

def _enum(**enums):
    return type('Enum', (), enums)

NETLOG_LINE_TYPE = _enum(INVALID = "Invalid",
                         SYSTEM = "System")

NETLOG_SHIP_STATUS = _enum(UNKNOWN = "unknown",
                           NORMAL_FLIGHT = "NormalFlight",
                           SUPERCRUISE = "Supercruise",
                           PROVING_GROUND = "ProvingGround")

class NetlogLineFactory():
    @staticmethod
    def get_line(line_time, line):
        parsed_line = _SystemLine.parse_netlog_line(line_time, line)
        if parsed_line is not None:
            return parsed_line
        else:
            return None

class _SystemLine(edevent.BaseEvent):
    def __init__(self,
                 line_time,
                 system_name,
                 num_bodies = 0,
                 position = (0.0, 0.0, 0.0),
                 ship_status = NETLOG_SHIP_STATUS.UNKNOWN):
        edevent.BaseEvent.__init__(self,NETLOG_LINE_TYPE.SYSTEM, line_time)

        self._name = system_name
        self._num_bodies = num_bodies
        self._position = position
        self._ship_status = ship_status
        
        # Even though this is for parsing a Netlog line
        # we are going to hack in the EDSM information
        # about this system.
        #
        # Why?
        #
        # Well for one this is the only place to get
        # access to all the information. Two, FD may
        # add a bunch of this information in at a 
        # later date and time.
        edsm_db = edsmdb.get_instance()
        
        self._distances = edsm_db.get_distances(self._name)

        system = edsm_db.get_system(self._name)
        if system:
            self._system_coordinates = system.position
        else:
            self._system_coordinates = None

    @classmethod
    def parse_netlog_line(cls, line_time, line):
        if (line.startswith("System:")):
            try:
                b, _, line = line.partition("(")
                b, _, line = line.partition("Body:")
                system = b[:len(b) - 2]
            except ValueError:
                return None

            try:
                b, _, line = line.partition("Pos:(")
                body = int(b)
            except ValueError:
                body = 0

            try:
                b, _, line = line.partition(")")
                pos = tuple(float(f) for f in b.split(","))
            except ValueError:
                pos = (0.0, 0.0, 0.0)
            
            try:
                status = line.strip()

                if status == str(NETLOG_SHIP_STATUS.NORMAL_FLIGHT):
                    status = NETLOG_SHIP_STATUS.NORMAL_FLIGHT
                elif status == str(NETLOG_SHIP_STATUS.SUPERCRUISE):
                    status = NETLOG_SHIP_STATUS.SUPERCRUISE
                elif status == str(NETLOG_SHIP_STATUS.PROVING_GROUND):
                    status = NETLOG_SHIP_STATUS.PROVING_GROUND
                else:
                    status = NETLOG_SHIP_STATUS.UNKNOWN
            except ValueError:
                status = NETLOG_SHIP_STATUS.UNKNOWN

            return cls(line_time, system, num_bodies = body, position = pos, ship_status = status)

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
            for distance in self._distances:
                item = dict()
                item['name'] = distance.sys2.name
                item['distance'] = distance.distance
                
                if distance.sys2.position:
                    item['coords'] = distance.sys2.position
                
                dict_list.append(item)
                
            json_dict['Distances'] = dict_list

    def get_name(self):
        return self._name

    def get_num_bodies(self):
        return self._num_bodies

    def get_position(self):
        return self._position

    def get_ship_status(self):
        return self._ship_status

    def __str__(self):
        return edevent.BaseEvent.__str__(self) + ", Name [" + self._name + "], Bodies [" + str(self._num_bodies) + "], Position [" + str(self._position) + "], Ship Status [" + self._ship_status + "]"

if __name__ == "__main__":
    system = _SystemLine(datetime.datetime.utcnow(), 'Prieluia ND-H b57-0', ship_status = NETLOG_SHIP_STATUS.SUPERCRUISE)
    print system.get_json()
