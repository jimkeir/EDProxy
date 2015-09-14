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
            self._config_parser.add_section('Netlog')
            self._config_parser.add_section('Image')
            
            self._config_parser.set('Version', 'version', '1')

            self._config_parser.set('Netlog', 'path', legacy_parser.get('Paths', 'netlog'))
            
            self._config_parser.set('Image', 'path', '')
            self._config_parser.set('Image', 'format', edpicture.IMAGE_CONVERT_FORMAT.BMP)
            self._config_parser.set('Image', 'convert_space', '')
            self._config_parser.set('Image', 'delete_after_convert', 'False')
            
            self.__write_config()            
        else:
            self._config_parser = ConfigParser.SafeConfigParser()
            
            self._config_parser.add_section('Version')
            self._config_parser.add_section('Netlog')
            self._config_parser.add_section('Image')

            self._config_parser.set('Version', 'version', '1')

            value = "C:\\Program Files (x86)\\Frontier\\EDLaunch\\Products\\FORC-FDEV-D-1010\\Logs"
            self._config_parser.set('Netlog', 'path', value)

            self._config_parser.set('Image', 'path', '')
            self._config_parser.set('Image', 'format', edpicture.IMAGE_CONVERT_FORMAT.BMP)
            self._config_parser.set('Image', 'convert_space', '')
            self._config_parser.set('Image', 'delete_after_convert', 'False')
            
            self.__write_config()
    
    def __write_config(self):
        with open(self._inifile) as outf:
            self._config_parser.write(outf)
        
    def get_config_version(self):
        return self._config_parser.get('Version', 'version')
    def get_netlog_path(self):
        return self._config_parser.get('Netlog', 'path')
    
    def get_image_path(self):
        return self._config_parser.get('Image', 'path')
    
    def get_image_format(self):
        return self._config_parser.get('Image', 'format')
    
    def get_image_convert_space(self):
        return self._config_parser.get('Image', 'convert_space')
    
    def get_image_delete_after_convert(self):
        return self._config_parser.get('Image', 'delete_after_convert')
    
    def set_netlog_path(self, path):
        self._config_parser.set('Netlog', 'path', path)
        self.__write_config()
        
    def set_image_path(self, path):
        self._config_parser.set('Image', 'path', path)
        self.__write_config()

    def set_image_format(self, format):
        self._config_parser.set('Image', 'format', format)
        self.__write_config()
        
    def set_image_convert_space(self, value):
        self._config_parser.set('Image', 'convert_space', value)
        self.__write_config()

    def set_image_delete_after_convert(self, value):
        self._config_parser.set('Image', 'delete_after_convert', str(value))
        self.__write_config()
        