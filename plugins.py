from _pyio import __metaclass__
from abc import abstractmethod
import abc

class ThirdPartyPlugin(object):
    __metaclass__ = abc.ABCMeta
    
    @abstractmethod
    def get_name(self):
        """ Get the name for this plugin. """
        
    @abstractmethod
    def get_last_interaction_time(self):
        """ Get the last time the plugin interacted with an event. """
        
    @abstractmethod
    def is_operational(self):
        """ Let Edproxy know that this 3rd party plugin is ready to take events. """

    @abstractmethod
    def post(self, event):
        """ Post a system event to the third party listener. """
        
class ThirdPartyPluginSettings(object):
    __metaclass__ = abc.ABCMeta
    
    @abstractmethod
    def do_layout(self, sizer):
        """ Add any UI layout elements into the given sizer. """
        
    @abstractmethod
    def do_properties(self):
        """ Setup all defaults, or properties. """
    
    @abstractmethod
    def on_ok(self):
        """ The OK button has been pressed. Save off any properties that have been modified. """
