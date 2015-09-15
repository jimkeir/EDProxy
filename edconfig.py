import edutils
import os
import ConfigParser
import edpicture

class EDConfig(object):
    def __init__(self):
        self._eduser_dir = os.path.join(edutils.get_user_dir(), ".edproxy")
        self._inifile = os.path.join(self._eduser_dir, "edproxy.ini")
        self._inifile_deprecated = os.path.join(edutils.get_app_dir(), "edproxy.ini")
        
        self.__load()
        
    def __load(self):
        if os.path.exists(self._inifile):
            self._config_parser = ConfigParser.SafeConfigParser()
            self._config_parser.read(self._inifile)
        elif os.path.exists(self._inifile_deprecated):
            self._config_parser = ConfigParser.SafeConfigParser()

            legacy_parser = ConfigParser.SafeConfigParser()
            legacy_parser.read(self._inifile_deprecated)
            
            self._config_parser.add_section('Version')
            self._config_parser.add_section('General')
            self._config_parser.add_section('Netlog')
            self._config_parser.add_section('Image')
            
            self._config_parser.set('Version', 'version', '1')

            self._config_parser.set('General', 'system_startup', 'False')
            self._config_parser.set('General', 'edproxy_startup', 'False')
            self._config_parser.set('General', 'start_minimized', 'False')

            self._config_parser.set('Netlog', 'path', legacy_parser.get('Paths', 'netlog'))
            
            self._config_parser.set('Image', 'path', '')
            self._config_parser.set('Image', 'format', edpicture.IMAGE_CONVERT_FORMAT.BMP)
            self._config_parser.set('Image', 'convert_space', '')
            self._config_parser.set('Image', 'delete_after_convert', 'False')
            self._config_parser.set('Image', 'name_replacement', '')
            
            self.__write_config()            
        else:
            self._config_parser = ConfigParser.SafeConfigParser()
            
            self._config_parser.add_section('Version')
            self._config_parser.add_section('General')
            self._config_parser.add_section('Netlog')
            self._config_parser.add_section('Image')

            self._config_parser.set('Version', 'version', '1')

            self._config_parser.set('General', 'system_startup', 'False')
            self._config_parser.set('General', 'edproxy_startup', 'False')
            self._config_parser.set('General', 'start_minimized', 'False')

            value = "C:\\Program Files (x86)\\Frontier\\EDLaunch\\Products\\FORC-FDEV-D-1010\\Logs"
            self._config_parser.set('Netlog', 'path', value)

            self._config_parser.set('Image', 'path', '')
            self._config_parser.set('Image', 'format', edpicture.IMAGE_CONVERT_FORMAT.BMP)
            self._config_parser.set('Image', 'convert_space', '')
            self._config_parser.set('Image', 'delete_after_convert', 'False')
            self._config_parser.set('Image', 'name_replacement', '')

            self.__write_config()
    
    def __write_config(self):
        with open(self._inifile, "w+") as outf:
            self._config_parser.write(outf)
        
    def get_config_version(self):
        return self._config_parser.get('Version', 'version')
    
    def get_system_startup(self):
        return (self._config_parser.get('General', 'system_startup') == 'True')
    
    def get_edproxy_startup(self):
        return (self._config_parser.get('General', 'edproxy_startup') == 'True')
    
    def get_start_minimized(self):
        return (self._config_parser.get('General', 'start_minimized') == 'True')
        
    def get_netlog_path(self):
        return self._config_parser.get('Netlog', 'path')
    
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

    def set_netlog_path(self, path):
        self._config_parser.set('Netlog', 'path', path)
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

        