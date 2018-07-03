import edutils
import os
import ConfigParser
import edpicture
import threading
import datetime
import logging
import urlparse

class EDConfig(object):
    def __init__(self):
        self._log = logging.getLogger("com.fussyware.edproxy")

        self._eduser_dir = edutils.get_edproxy_dir()
        
        if not os.path.exists(self._eduser_dir):
            os.makedirs(self._eduser_dir)

        self._inifile = os.path.join(self._eduser_dir, "edproxy.ini")
        self._inifile_deprecated = os.path.join(edutils.get_app_dir(), "edproxy.ini")
        
        self._version = '4'
        
        self._timer = None
        self._cancel_time = None
        self._lock = threading.Lock()

        self._was_created = False
        self._was_upgraded = False
        
        # Python issue7980 bug workaround
        datetime.datetime.strptime('2012-01-01', '%Y-%m-%d')

        self.__load()
        
    def __load(self):
        if os.path.exists(self._inifile):
            self._config_parser = ConfigParser.SafeConfigParser()
            self._config_parser.read(self._inifile)
            
            self.add_config_section('Version')
            self.add_config_section('General')
            self.add_config_section('Discovery')
            self.add_config_section('Netlog')
            self.add_config_section('Image')
            self.add_config_section('Journal')

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
            self.add_config_section('Discovery')
            self.set_discovery_ttl(self.get_discovery_ttl())
            self.__write_config()

            self._was_upgraded = True
            
            old_value = '2'
        
        if old_value == '2':
            value = self.__find_appconfig_path()
            
            if len(value) == 0:
                log_path = self.get_netlog_path()
                
                if len(log_path) > 0:
                    config_path, _ = os.path.split(os.path.normpath(log_path))
                    
                    if (os.path.exists(os.path.join(config_path, "AppConfig.xml"))):
                        value = config_path
            
            self.set_netlog_path(value)
            self.__write_config()
            
            self._was_upgraded = True
            
            old_value = '3'

        if old_value == '3':
            self.add_config_section('Journal')

            self.set_journal_path(self.get_journal_path())
            self.set_local_system_db(self.get_local_system_db())
            self.__write_config()
            
            self._was_upgraded = True
            
            old_value = '4'

    def __create_default_config(self, legacy_parser = None):
            self._config_parser = ConfigParser.SafeConfigParser()
            
            self.add_config_section('Version')
            self.add_config_section('General')
            self.add_config_section('Discovery')
            self.add_config_section('Netlog')
            self.add_config_section('Image')
            self.add_config_section('Journal')

            self._config_parser.set('Version', 'version', self._version)

            self.set_system_startup(self.get_system_startup())
            self.set_edproxy_startup(self.get_edproxy_startup())
            self.set_start_minimized(self.get_start_minimized())

            self.set_discovery_ttl(self.get_discovery_ttl())
            
            self.set_netlog_path(self.get_netlog_path())
            self.set_journal_path(self.get_journal_path())
            self.set_appconfig_path(self.get_appconfig_path())
            
            self.set_image_path(self.get_image_path())
            self.set_image_format(self.get_image_format())
            self.set_image_convert_space(self.get_image_convert_space())
            self.set_image_delete_after_convert(self.get_image_delete_after_convert())
            self.set_image_name_replacement(self.get_image_name_replacement())

            self.__write_config()
            
            self._was_created = True
        
    def __write_selfprotected(self):
            with open(self._inifile, "w+") as outf:
                self._log.debug("Start write out config")
                self._config_parser.write(outf)
                self._log.debug("Done write out config")
                
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

                self._timer = threading.Timer(5.0, self.__write_config_timeout)
                self._timer.start()
            finally:
                self._lock.release()
        
    def __find_netlog_path(self):
        potential_paths = edutils.get_potential_log_dirs()

        for edpath in potential_paths:
            if os.path.exists(edpath):
                return edpath

        return ""
    
    def default_journal_path(self):
        return os.path.join(edutils.get_user_dir(),'Saved Games/Frontier Developments/Elite Dangerous')

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
    
    @staticmethod
    def get_version():
        return "2.4"
    
    def get_config_version(self):
        try:
            return self._version
        except:
            return '0'
    
    def get_system_startup(self):
        try:
            return (self._config_parser.get('General', 'system_startup') == 'True')
        except:
            return 'False'
    
    def get_update_baseURL(self):
        try:
            serverURL = self._config_parser.get('General', 'update_server_url')
            if not urlparse.urlparse(serverURL).scheme:
                raise ValueException

            return serverURL
        except:
            return 'https://github.com/jimkeir/EDProxy/releases'

    def get_edproxy_startup(self):
        try:
            return (self._config_parser.get('General', 'edproxy_startup') == 'True')
        except:
            return 'False'
    
    def get_start_minimized(self):
        try:
            return (self._config_parser.get('General', 'start_minimized') == 'True')
        except:
            return 'False'
        
    def get_local_system_db(self):
        try:
            return (self._config_parser.get('General', 'local_system_database') == 'True')
        except:
            return 'False'
       
    def get_discovery_ttl(self):
        try:
           return int(self._config_parser.get('Discovery', 'ttl'))
        except:
            return 1
    
    def get_netlog_path(self):
        try:
            return self._config_parser.get('Netlog', 'path')
        except:
            if legacy_parser:
                return legacy_parser.get('Paths', 'netlog')
            else:
                return self.__find_netlog_path()

    def get_journal_path(self):
        try:
            return self._config_parser.get('Journal', 'path')
        except:
            return self.default_journal_path()
    
    def get_appconfig_path(self):
        try:
            return self._config_parser.get('Netlog', 'appconfig_path')
        except:
            return self.__find_appconfig_path()
    
    def get_image_path(self):
        try:
           return self._config_parser.get('Image', 'path')
        except:
            return ''
    
    def get_image_name_replacement(self):
        try:
           return self._config_parser.get('Image', 'name_replacement')
        except:
            return ''
    
    def get_image_format(self):
        try:
           return self._config_parser.get('Image', 'format')
        except:
            return edpicture.IMAGE_CONVERT_FORMAT.BMP
    
    def get_image_convert_space(self):
        try:
           return self._config_parser.get('Image', 'convert_space')
        except:
            return ''
    
    def get_image_delete_after_convert(self):
        try:
           return (self._config_parser.get('Image', 'delete_after_convert') == 'True')
        except:
            return 'False'
    
    def set_system_startup(self, value):
        self._config_parser.set('General', 'system_startup', str(value))
        self.__write_config()
        
    def set_edproxy_startup(self, value):
        self._config_parser.set('General', 'edproxy_startup', str(value))
        self.__write_config()

    def set_start_minimized(self, value):
        self._config_parser.set('General', 'start_minimized', str(value))
        self.__write_config()
        
    def set_local_system_db(self, value):
        self._config_parser.set('General', 'local_system_database', str(value))
        self.__write_config()
        
    def set_discovery_ttl(self, value):
        self._config_parser.set('Discovery', 'ttl', str(value))

    def set_netlog_path(self, path):
        self._config_parser.set('Netlog', 'path', path)
        self.__write_config()

    def set_journal_path(self, path):
        self._config_parser.set('Journal', 'path', path)
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

    def add_config_section(self, section):
        try:
            self._config_parser.add_section(section)
        except(ConfigParser.DuplicateSectionError):
            pass

_config_singleton = EDConfig()
def get_instance():
    return _config_singleton

# if __name__ == "__main__":
#     config = get_instance()
#     print config.find_netlog_path()
