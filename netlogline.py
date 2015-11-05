import json
import edevent

__all__ = [ 'NETLOG_LINE_TYPE', 'NETLOG_SHIP_STATUS', 'NetlogLineFactory' ]

def _enum(**enums):
    return type('Enum', (), enums)

NETLOG_LINE_TYPE = _enum(INVALID = "Invalid",
                         SYSTEM = "System")

NETLOG_SHIP_STATUS = _enum(UNKNOWN = "unknown",
                           CRUISING = "cruising")

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
                 position = (0, 0, 0),
                 ship_status = NETLOG_SHIP_STATUS.CRUISING):
        edevent.BaseEvent.__init__(self,NETLOG_LINE_TYPE.SYSTEM, line_time)

        self._name = system_name
        self._num_bodies = num_bodies
        self._position = position
        self._ship_status = ship_status

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

                if status == str(NETLOG_SHIP_STATUS.CRUISING):
                    status = NETLOG_SHIP_STATUS.CRUISING
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
