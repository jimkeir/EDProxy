import edevent
import datetime
import json

__all__ = [ 'JournalLineFactory' ]

def _enum(**enums):
    return type('Enum', (), enums)

JOURNAL_VERSION = _enum(VERSION_2_1 = "2.1+")

class JournalLineFactory():
    @staticmethod
    def get_line(line_time, line):
        parsed_line = _JournalLine.parse_journal_line(line_time, line)
        
        return parsed_line

class _JournalLine(edevent.BaseEvent):
    def __init__(self,
                 version,
                 line_time,
                 line_json):
        edevent.BaseEvent.__init__(self, 'Journal', line_time)

        self._version = version
        self._line_json = line_json
        self._event_type = line_json['event'];

    @classmethod
    def parse_journal_line(cls, line_time, line):
        if 'timestamp' in line and 'event' in line:
            return cls(JOURNAL_VERSION.VERSION_2_1,
                       line_time,
                       line)
        else:
            return None

    def _fill_json_dict(self, json_dict):
        json_dict['Entry'] = self._line_json

    def __str__(self):
        return edevent.BaseEvent.__str__(self) + ", Event [" + self._event_type + "]"

