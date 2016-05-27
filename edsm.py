import ConfigParser
import netlogline
import urllib
import urllib2
import threading
import edutils
import os
import edconfig
import edparser
import time
import datetime
import wx
import logging
import plugins
from netlogline import NETLOG_VERSION
from edconfig import EDConfig

class EDSMConfig(object):
    def __init__(self):
        self._inifile = os.path.join(edutils.get_edproxy_dir(), "edsm.ini")
        self._version = '1'
        self._timer = None
        self._cancel_time = None
        self._lock = threading.Lock()
        
        self.__load()
        
    def __load(self):
        if os.path.exists(self._inifile):
            self._config_parser = ConfigParser.SafeConfigParser()
            self._config_parser.read(self._inifile)
            
            version = self._config_parser.get('Version', 'version')
            self.__upgrade(version, self._version)
        else:
            self.__create_default_config()

    def __upgrade(self, old_value, new_value):
        pass

    def __create_default_config(self, legacy_parser = None):
        self._config_parser = ConfigParser.SafeConfigParser()
        
        self._config_parser.add_section('Version')
        self._config_parser.add_section('General')

        self._config_parser.set('Version', 'version', self._version)

        self._config_parser.set('General', 'api_key', '')
        self._config_parser.set('General', 'cmdr_name', '')
        self._config_parser.set('General', 'last_time', '')
        self._config_parser.set('General', 'last_system', '')
        
        self.__write_config(True)

    def __write_selfprotected(self):
            with open(self._inifile, "w+") as outf:
                self._config_parser.write(outf)
                
            self._timer = None
            self._cancel_time = None

    def __write_config_timeout(self):
        try:
            self._lock.acquire()
            self.__write_selfprotected()
        finally:
            self._lock.release()

    def __write_config(self, force = False):
        if force:
            self.__write_config_timeout()
        else:
            try:
                self._lock.acquire()
                if self._timer:
                    self._timer.cancel()

                    if not self._cancel_time:
                        self._cancel_time = datetime.datetime.utcnow()
                    else:
                        _t = datetime.datetime.utcnow()
                        
                        if (_t - self._cancel_time).total_seconds() > 10:
                            self.__write_selfprotected()
                    
                self._timer = threading.Timer(1.0, self.__write_config_timeout)
                self._timer.start()
            finally:
                self._lock.release()
        
    def get_config_version(self):
        return self._version

    def get_api_key(self):
        return self._config_parser.get('General', 'api_key')

    def get_cmdr_name(self):
        return self._config_parser.get('General', 'cmdr_name')

    def get_last_time(self):
        _time = self._config_parser.get('General', 'last_time')
        
        if not _time:
            return datetime.datetime.utcfromtimestamp(0)
        else:
            return datetime.datetime.strptime(_time, '%Y-%m-%d %H:%M:%S')
    
    def get_last_system(self):
        return self._config_parser.get('General', 'last_system')
    
    def set_api_key(self, key):
        self._config_parser.set('General', 'api_key', key)
        self.__write_config()

    def set_cmdr_name(self, name):
        self._config_parser.set('General', 'cmdr_name', name)
        self.__write_config()

    def set_last_time(self, entry):
        self._config_parser.set('General', 'last_time', entry.strftime('%Y-%m-%d %H:%M:%S'))
        self.__write_config()

    def set_last_system(self, system):
        self._config_parser.set('General', 'last_system', system)
        self.__write_config()

_config_singleton = EDSMConfig()
def get_config_instance():
    return _config_singleton

class EDSMSettings(plugins.ThirdPartyPluginSettings):
    def __init__(self, parent):
        self._config = get_config_instance()
        
        self._api_text = wx.TextCtrl(parent)
        self._cmdr_name = wx.TextCtrl(parent)
        
        self._parent = parent
        
    def do_layout(self, sizer):
        sizer1 = wx.StaticBoxSizer(wx.StaticBox(self._parent, label = "Elite: Dangerous Star Map (EDSM)"), wx.VERTICAL)

        grid1 = wx.FlexGridSizer(rows = 2, cols = 2, hgap = 2, vgap = 5)

        grid1.Add(wx.StaticText(self._parent, wx.ID_ANY, _("API Key:"), style=wx.ST_NO_AUTORESIZE), flag = wx.ALIGN_RIGHT)
        grid1.Add(self._api_text, flag = wx.EXPAND)

        grid1.Add(wx.StaticText(self._parent, wx.ID_ANY, _("CMDR Name:"), style=wx.ST_NO_AUTORESIZE), flag = wx.ALIGN_RIGHT)
        grid1.Add(self._cmdr_name, flag = wx.EXPAND)
        
        grid1.AddGrowableCol(1, proportion = 1)
        
        sizer1.Add(grid1, 0, wx.EXPAND | wx.ALL)        
        sizer.Add(sizer1, 0, wx.EXPAND)
    
    def do_properties(self):
        self._api_text.ChangeValue(self._config.get_api_key())
        self._cmdr_name.ChangeValue(self._config.get_cmdr_name())

    def on_ok(self):
        self._config.set_api_key(self._api_text.GetValue())
        self._config.set_cmdr_name(self._cmdr_name.GetValue())
    
class EDSM(plugins.ThirdPartyPlugin):
    def __init__(self):
        self._log = logging.getLogger("com.fussyware.edproxy")
        self._config = get_config_instance()
    
    def is_operational(self):
        return ((self._config.get_api_key() != '') and (self._config.get_cmdr_name() != ''))
    
    def get_name(self):
        return "EDSM"

    def get_last_interaction_time(self):
        return self._config.get_last_time()
    
    def get_config(self):
        return self._config
    
    def post(self, event):
        ret = False
        
        if self.is_operational() and event.get_name() != self._config.get_last_system() and event.get_line_type() == netlogline.NETLOG_LINE_TYPE.SYSTEM:
            _cmdr = self._config.get_cmdr_name()
            _apikey = self._config.get_api_key()
            _time = time.strftime('%Y-%m-%d %H:%M:%S', event.get_timeutc())
            _name = event.get_name()
            
            self._config.set_last_time(event.get_time())
            self._config.set_last_system(_name)
            
            _url = "http://www.edsm.net/api-logs-v1/set-log?fromSoftware=%s&fromSoftwareVersion=%s&commanderName=%s&apiKey=%s&systemName=%s&dateVisited=%s" % ("edproxy", EDConfig.get_version(),urllib.quote_plus(_cmdr), urllib.quote_plus(_apikey), urllib.quote_plus(_name), urllib.quote_plus(_time))

            if event.get_version() == NETLOG_VERSION.VERSION_2_1 and event.get_system_coordinates():
                position = event.get_system_coordinates()
                _url = "%s&x=%s&y=%s&z=%s" % (_url,
                                              urllib.quote_plus(str(position[0])),
                                              urllib.quote_plus(str(position[1])),
                                              urllib.quote_plus(str(position[2])))
                             
            self._log.debug(_url)
            response = urllib2.urlopen(_url)

            ret = (response.getcode() == 200)
            
        return ret

def __log_parser(event, edsm_listener):
    edsm_listener.post(event)
    
if __name__ == "__main__":
    config_path, _ = os.path.split(os.path.normpath(edconfig.get_instance().get_netlog_path()))
    config_path = os.path.join(config_path, "AppConfig.xml")

    print '1'
    edsm_listener = EDSM()
    print '2'
    
    print '3'
    _config = edsm_listener.get_config()
    _config.set_api_key("890a4614a38f92dfe5bb9419ff8222d422152b58")
    _config.set_cmdr_name("Duck Rodgers")
    print '4'
    
    _t0 = datetime.datetime.utcnow()
    edparser.EDNetlogParser.parse_past_logs("/Users/wes/src/pydev/edproxy/test", #edconfig.get_instance().get_netlog_path(),
                                            "netLog",
                                            __log_parser,
                                            args = (edsm_listener, ),
                                            start_time = _config.get_last_time())
    print '5', (datetime.datetime.utcnow() - _t0)

    time.sleep(5.0)