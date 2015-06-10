import json

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

class _NetlogLine():
    def __init__(self, line_time):
        self._time = line_time

    def get_line_type(self):
        raise ValueError("This is an interface and not intended for public use.")

    def get_time(self):
        return self._time
        
    def get_json(self):
        raise ValueError("This is an interface and not intended for public use.")

    def _get_json_header(self):
        ret = dict()
        
        ret['Date'] = self._time.isoformat()
        ret['Type'] = str(self.get_line_type())

        return ret

    def __str__(self):
        return "Time [" + self._time.isoformat() + "]"

class _SystemLine(_NetlogLine):
    def __init__(self,
                 line_time,
                 system_name,
                 num_bodies = 0,
                 position = (0, 0, 0),
                 ship_status = NETLOG_SHIP_STATUS.CRUISING):
        _NetlogLine.__init__(self, line_time)

        self._name = system_name
        self._num_bodies = num_bodies
        self._position = position
        self._ship_status = ship_status

    @classmethod
    def parse_netlog_line(cls, line_time, line):
        if (line.startswith("System:")):
            try:
                b, sep, line = line.partition("(")
                b, sep, line = line.partition("Body:")
                system = b[:len(b) - 2]
            except ValueError, e:
                return None

            try:
                b, sep, line = line.partition("Pos:(")
                body = int(b)
            except ValueError, e:
                body = 0

            try:
                b, sep, line = line.partition(")")
                pos = tuple(float(f) for f in b.split(","))
            except ValueError, e:
                pos = (0.0, 0.0, 0.0)
            
            try:
                status = line.strip()

                if status == str(NETLOG_SHIP_STATUS.CRUISING):
                    status = NETLOG_SHIP_STATUS.CRUISING
                else:
                    status = NETLOG_SHIP_STATUS.UNKNOWN
            except ValueError, e:
                status = NETLOG_SHIP_STATUS.UNKNOWN

            return cls(line_time, system, num_bodies = body, position = pos, ship_status = status)

        return None

    def get_line_type(self):
        return NETLOG_LINE_TYPE.SYSTEM

    def get_json(self):
        value = self._get_json_header()
        value['System'] = self._name
        value['Bodies'] = self._num_bodies
        value['Position'] = self._position
        value['Status'] = self._ship_status

        return json.dumps(value)
        # return json.dumps([{ 'Date': self.get_time().isoformat(),
        #                      'System': self._name,
        #                      'Bodies': self._num_bodies,
        #                      'Position': self._position,
        #                      'Status': self._ship_status }])

    def get_name(self):
        return self._name

    def get_num_bodies(self):
        return self._num_bodies

    def get_position(self):
        return self._position

    def get_ship_status(self):
        return self._ship_status

    def __str__(self):
        return _NetlogLine.__str__(self) + ", Name [" + self._name + "], Bodies [" + str(self._num_bodies) + "], Position [" + str(self._position) + "], Ship Status [" + self._ship_status + "]"
