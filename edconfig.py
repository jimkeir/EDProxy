import edutils
import os
import ConfigParser
import edpicture
import threading
import datetime
import sys
from __builtin__ import False

class EDConfig(object):
    def __init__(self):
        self._eduser_dir = edutils.get_edproxy_dir()
        
        if not os.path.exists(self._eduser_dir):
            os.makedirs(self._eduser_dir)

        self._inifile = os.path.join(self._eduser_dir, "edproxy.ini")
        self._inifile_deprecated = os.path.join(edutils.get_app_dir(), "edproxy.ini")
        
        self._version = '3'
        
        self._timer = None
        self._cancel_time = None
        self._lock = threading.Lock()

        self._was_created = False
        self._was_upgraded = False
        
        self.__load()
        
    def __load(self):
        if os.path.exists(self._inifile):
            self._config_parser = ConfigParser.SafeConfigParser()
            self._config_parser.read(self._inifile)
            
            version = self._config_parser.get('Version', 'version')
            self.__upgrade(version, self._version)
        elif os.path.exists(self._inifile_deprecated):
            self._config_parser = ConfigParser.SafeConfigParser()

            legacy_parser = ConfigParser.SafeConfigParser()
            legacy_parser.read(self._inifile_deprecated)

            self.__create_default_config(legacy_parser)
        else:
            self._config_parser = ConfigParser.SafeConfigParser()
            self.__create_default_config()

    def __upgrade(self, old_value, new_value):
        self._config_parser.set('Version', 'version', new_value)

        if old_value == '1':            
            self._config_parser.add_section('Discovery')
            self._config_parser.set('Discovery', 'ttl', '1')
            self.__write_config()

            self._was_upgraded = True
            
            old_value = '2'
        
        if old_value == '2':
            value = self.__find_appconfig_path()
            
            if len(value) == 0:
                log_path = self.get_netlog_path()
                
                if len(log_path) > 0:
                    config_path, _ = os.path.split(os.path.normpath(log_path))
                    config_path = os.path.join(config_path, "AppConfig.xml")
                    
                    if (os.path.exists(config_path)):
                        value = config_path
                
            self._config_parser.set('Netlog', 'appconfig_path', value)
            self.__write_config()
            
            self._was_upgraded = True
            
            old_value = '3'

    def __create_default_config(self, legacy_parser = None):
            self._config_parser = ConfigParser.SafeConfigParser()
            
            self._config_parser.add_section('Version')
            self._config_parser.add_section('General')
            self._config_parser.add_section('Discovery')
            self._config_parser.add_section('Netlog')
            self._config_parser.add_section('Image')

            self._config_parser.set('Version', 'version', self._version)

            self._config_parser.set('General', 'system_startup', 'False')
            self._config_parser.set('General', 'edproxy_startup', 'False')
            self._config_parser.set('General', 'start_minimized', 'False')

            self._config_parser.set('Discovery', 'ttl', '1')
            
            if legacy_parser:
                self._config_parser.set('Netlog', 'path', legacy_parser.get('Paths', 'netlog'))
            else:
                self._config_parser.set('Netlog', 'path', self.__find_netlog_path())

            self._config_parser.set('Netlog', 'appconfig_path', self.__find_appconfig_path())
            
            self._config_parser.set('Image', 'path', '')
            self._config_parser.set('Image', 'format', edpicture.IMAGE_CONVERT_FORMAT.BMP)
            self._config_parser.set('Image', 'convert_space', '')
            self._config_parser.set('Image', 'delete_after_convert', 'False')
            self._config_parser.set('Image', 'name_replacement', '')

            self.__write_config()
            
            self._was_created = True
        
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
        
    def __find_netlog_path(self):
        potential_paths = edutils.get_potential_log_dirs()

        for edpath in potential_paths:
            if os.path.exists(edpath):
                return edpath

        return ""
    
    def __find_appconfig_path(self):
        potential_paths = edutils.get_potential_appconfig_dirs()

        for edpath in potential_paths:
            if os.path.exists(os.path.join(edpath, "AppConfig.xml")):
                return edpath

        return ""
    
    def was_created(self):
        return self._was_created
    
    def was_upgraded(self):
        return self._was_upgraded
    
    def get_config_version(self):
        return self._version
    
    def get_system_startup(self):
        return (self._config_parser.get('General', 'system_startup') == 'True')
    
    def get_edproxy_startup(self):
        return (self._config_parser.get('General', 'edproxy_startup') == 'True')
    
    def get_start_minimized(self):
        return (self._config_parser.get('General', 'start_minimized') == 'True')
        
    def get_discovery_ttl(self):
        return int(self._config_parser.get('Discovery', 'ttl'))
    
    def get_netlog_path(self):
        return self._config_parser.get('Netlog', 'path')
    
    def get_appconfig_path(self):
        return self._config_parser.get('Netlog', 'appconfig_path')
    
    def get_image_path(self):
        return self._config_parser.get('Image', 'path')
    
    def get_image_name_replacement(self):
        return self._config_parser.get('Image', 'name_replacement')
    
    def get_image_format(self):
        return self._config_parser.get('Image', 'format')
    
    def get_image_convert_space(self):
        return self._config_parser.get('Image', 'convert_space')
    
    def get_image_delete_after_convert(self):
        return (self._config_parser.get('Image', 'delete_after_convert') == 'True')
    
    def set_system_startup(self, value):
        self._config_parser.set('General', 'system_startup', str(value))
        self.__write_config()
        
    def set_edproxy_startup(self, value):
        self._config_parser.set('General', 'edproxy_startup', str(value))
        self.__write_config()

    def set_start_minimized(self, value):
        self._config_parser.set('General', 'start_minimized', str(value))
        self.__write_config()
        
    def set_discovery_ttl(self, value):
        self._config_parser.set('Discovery', 'ttl', str(value))

    def set_netlog_path(self, path):
        self._config_parser.set('Netlog', 'path', path)
        self.__write_config()
        
    def set_appconfig_path(self, path):
        self._config_parser.set('Netlog', 'appconfig_path', path)
        self.__write_config()
        
    def set_image_path(self, path):
        self._config_parser.set('Image', 'path', path)
        self.__write_config()

    def set_image_name_replacement(self, value):
        self._config_parser.set('Image', 'name_replacement', value)
        self.__write_config()
        
    def set_image_format(self, image_format):
        self._config_parser.set('Image', 'format', image_format)
        self.__write_config()
        
    def set_image_convert_space(self, value):
        self._config_parser.set('Image', 'convert_space', value)
        self.__write_config()

    def set_image_delete_after_convert(self, value):
        self._config_parser.set('Image', 'delete_after_convert', str(value))
        self.__write_config()

_config_singleton = EDConfig()
def get_instance():
    return _config_singleton

if __name__ == "__main__":
    config = get_instance()
    print config.get_appconfig_path()