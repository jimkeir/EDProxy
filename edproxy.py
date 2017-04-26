#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# generated by wxGlade 0.6.8 on Wed Jun 10 12:56:29 2015
#

import wx

# begin wxGlade: dependencies
import gettext
# end wxGlade

# begin wxGlade: extracode
# end wxGlade

import os, sys
import threading
import logging.handlers

import edutils
import ednet
import edparser
import edconfig
import edsettings
import edpicture
import netlogline
import edimport
import edupdate
from edicon import edicon
from edsm import EDSM
from __builtin__ import range
import edsendkeys

import edsmdb
from edconfig import EDConfig
# import datetime

class EDProxyFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        self.log = logging.getLogger("com.fussyware.edproxy");
        self.log.setLevel(logging.DEBUG)
        
        # begin wxGlade: EDProxyFrame.__init__
        kwds["style"] = wx.CAPTION | wx.CLOSE_BOX | wx.MINIMIZE_BOX | wx.CLIP_CHILDREN
        wx.Frame.__init__(self, *args, **kwds)

        menu_bar = wx.MenuBar()
        settings_menu = wx.Menu()
        self._import_menu = settings_menu.Append(wx.ID_ANY, "&Import\tCTRL+I")
        pref_menu = settings_menu.Append(wx.ID_PREFERENCES, "&Preferences\tCTRL+,", "Configure Edproxy Settings.")
        exit_menu = settings_menu.Append(wx.ID_EXIT, "&Exit", "Exit Edproxy.")
        menu_bar.Append(settings_menu, "&File")
        self.SetMenuBar(menu_bar)
        
        self._import_menu.Enable(False)
        
        self.start_button = wx.Button(self, wx.ID_ANY, _("Start"))
        self.stop_button = wx.Button(self, wx.ID_ANY, _("Stop"))
        
        self.client_listview = wx.ListView(self, style = wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.plugin_listview = wx.ListView(self, style = wx.LC_REPORT | wx.BORDER_SUNKEN)
        
        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_MENU, self.__on_import_menu, self._import_menu)
        self.Bind(wx.EVT_MENU, self.__on_pref_menu, pref_menu)
        self.Bind(wx.EVT_MENU, self.__on_exit_menu, exit_menu)
        self.Bind(wx.EVT_BUTTON, self.on_start, self.start_button)
        self.Bind(wx.EVT_BUTTON, self.on_stop, self.stop_button)
        
        # end wxGlade

        self.Bind(wx.EVT_CLOSE, self.on_win_close)
        
        self._edconfig = edconfig.get_instance()

        wx.CallLater(10, self.__finish_init_thread)

#         if self._edconfig.get_start_minimized():
#             print "hide"

    def __set_properties(self):
        # begin wxGlade: EDProxyFrame.__set_properties
        self.SetTitle(_("Elite: Dangerous Proxy - v" + EDConfig.get_version()))
        self.SetIcon(edicon.GetIcon())
#         self.SetIcon(wx.Icon('edicon.ico', wx.BITMAP_TYPE_ICO))
        self.SetMinClientSize(wx.Size(400, -1))
        self.SetMinSize(wx.Size(400, -1))
        self.stop_button.Enable(False)
        self.client_listview.InsertColumn(0, "Connected IP Address", width = wx.LIST_AUTOSIZE_USEHEADER)
        self.client_listview.InsertColumn(1, "Port", width = wx.LIST_AUTOSIZE)
        self.plugin_listview.InsertColumn(0, "Third-Party Plugin")
        self.plugin_listview.InsertColumn(1, "Status")
        self.plugin_listview.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.plugin_listview.SetColumnWidth(1, 200)
        # end wxGlade

        self._lock = threading.Lock()
        self._ui_conditional = threading.Condition(self._lock)
        self._client_list = list()
        
        self._netlog_parser = edparser.EDNetlogMonitor()
        self._netlog_parser.add_listener(self.__on_async_parser_event)

        self._journal_parser = edparser.EDJournalMonitor()
        self._journal_parser.add_listener(self.__on_async_parser_event)
        
        self._edpicture = edpicture.EDPictureMonitor()
        self._edpicture.add_listener(self.__on_new_image)        

        self._discovery_service = ednet.EDDiscoveryService("239.45.99.98", 45551)
        self._discovery_service.add_listener(self.__on_new_message)

        self._proxy_server = ednet.EDProxyServer(45550)
        self._proxy_server.add_listener(self.__on_new_client)
        
        self._websocket_server = ednet.EDProxyWebServer(8097)
        self._websocket_server.add_listener(self.__on_new_client)

        self._plugin_operational_list = list()
        self._plugin_list = list()
        
        self._plugin_list.append(EDSM())

    def __do_layout(self):
        # begin wxGlade: EDProxyFrame.__do_layout
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        
        sizer_5.Add(self.start_button, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_5.Add(self.stop_button, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_3.Add(self.client_listview, 0, wx.ALL | wx.EXPAND, 0)
        sizer_3.AddSpacer(1)
        sizer_3.Add(self.plugin_listview, 0, wx.ALL | wx.EXPAND, 0)
        sizer_3.AddSpacer(5)
        sizer_3.Add(sizer_5, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer_3.AddSpacer(2)

        self.SetSizer(sizer_3)
#         sizer_3.Fit(self)
        self.Layout()
        self.SetSize(self.GetEffectiveMinSize())
        self.Centre()
        # end wxGlade

    def __ui_thread_caller(self, func, *args, **kwargs):
        func(*args, **kwargs)

        with self._lock:
            self._ui_conditional.notify()
    
    def __run_on_ui_thread(self, func, *args, **kwargs):
        wx.CallAfter(self.__ui_thread_caller, func, *args, **kwargs)

        with self._lock:
            self._ui_conditional.wait()
        
    def __finish_init_thread(self):
        if self._edconfig.was_created():
            message = "Welcome to Edproxy!\n\n"
            message = message + "Edproxy allows you to send notifications out to other applications.\n\n"
            message = message + "From within Settings you may set your E:D log, and AppConfig.xml, paths. Defaults will be chosen for you for normal installations.\n\n"
            message = message + "You may also configure how you wish Edproxy to start-up and where to look for new E:D images."
            msg = wx.MessageDialog(parent = self,
                                   message = message,
                                   caption = "Welcome!",
                                   style = wx.OK | wx.ICON_INFORMATION)
            msg.ShowModal()
            msg.Destroy()

            settings = edsettings.EDSettings(self, wx.ID_ANY, "Settings Configuration")
            settings.ShowModal()
            settings.Destroy()
        elif self._edconfig.was_upgraded():
            message = "Edproxy has been successfully upgraded to version " + EDConfig.get_version() + "\n\n"
            message = message + "New to this release is:\n"
            message = message + "- Support for sending journal entries!\n"

            msg = wx.MessageDialog(parent = self,
                                   message = message,
                                   caption = "Upgrade to Version " + EDConfig.get_version(),
                                   style = wx.OK | wx.ICON_INFORMATION)
            msg.ShowModal()
            msg.Destroy()
            
        paths_are_good = False
        
        while not paths_are_good:
            netlog_path = self._edconfig.get_netlog_path()
            journal_path = self._edconfig.get_journal_path()
            appconfig_path = self._edconfig.get_appconfig_path()
             
            if not netlog_path or not appconfig_path or not os.path.exists(netlog_path) or not os.path.exists(os.path.join(appconfig_path, "AppConfig.xml")):
                message = "Could not locate E:D logging directory, or configuration directory. "
                message = message + "Please update the settings providing the appropriate directories.\n\n"
                message = message + "Some common log directories are:\n"
                
                for p in edutils.get_potential_log_dirs():
                    message = message + p + "\n"
            
                message = message + "\nSome common AppConfig directories are:\n"
        
                for p in edutils.get_potential_appconfig_dirs():
                    message = message + p + "\n"
            
                msg = wx.MessageDialog(parent = self,
                                       message = message,
                                       caption = "Verbose Logging Setup Error",
                                       style = wx.OK | wx.ICON_EXCLAMATION)
                msg.ShowModal()
                msg.Destroy()
        
                settings = edsettings.EDSettings(self, wx.ID_ANY, "Settings Configuration")
                settings.ShowModal()
                settings.Destroy()
            else:
                paths_are_good = True

        if self._edconfig.get_edproxy_startup():
            wx.PostEvent(self.GetEventHandler(), wx.PyCommandEvent(wx.EVT_BUTTON.typeId, self.start_button.GetId()))

        if sys.platform == "win32":
            self._updater = edupdate.EDWin32Updater(self, EDConfig.get_version())#, base_url="file:///D:/Temp")
        elif sys.platform == "darwin":
            self._updater = edupdate.EDMacOSXUpdater(self, EDConfig.get_version())#, base_url="file:///Users/wes/src/pydev/edproxy/testbed")
        
        self.Bind(edupdate.EVT_UPGRADE_EVENT, self.__on_upgrade)
        
    def __edsm_on_progress(self, msg):
        self._edsm_progress_dialog.Pulse(newmsg = msg)
        
    def __edsm_on_update(self):
        try:
            event = edsmdb.StarMapDbUpdatedEvent()
            
            self.log.debug("Sending new edsm event: [%s]", event) 
            self._lock.acquire()
            for client in self._client_list:
                client.send(event)
        finally:
            self._lock.release()
    
    def __stop(self):
        if not self.start_button.IsEnabled():
            self.log.debug("Stop discovery service")
            self._discovery_service.stop()
            self.log.debug("Stop Proxy server")
            self._proxy_server.stop()
            self.log.debug("Stop Websocket Proxy server")
            self._websocket_server.stop()
            self.log.debug("Stop netlog parser")
            self._netlog_parser.stop()
            self.log.debug("Stop image acquisition service")
            self._edpicture.stop()
            self.log.debug("Stopping EDSM database background updater")
            edsmdb.get_instance().close()

            self.log.debug("Stop all proxy clients and 3rd party plugins")
            self.client_listview.DeleteAllItems()
            self.plugin_listview.DeleteAllItems()
            
            for client in self._client_list:
                client.close()

            del self._client_list[:]
            del self._plugin_operational_list[:]
            
            self._client_list = list()
            self._plugin_operational_list = list()
            
            self.log.debug("All services stopped")
        
    def __on_upgrade(self, event):
        msg = wx.MessageDialog(parent = self,
                               message = "An update for Edproxy is available. Proceed with update?",
                               caption = "Edproxy Update Available",
                               style = wx.CANCEL | wx.OK | wx.ICON_INFORMATION | wx.CENTRE)
        
        if msg.ShowModal() == wx.ID_OK:
            self.__stop()
            
            # We will NEVER return from HERE!
            event.get_updater().perform_update(event.get_upgrade_file_path())
            
        event.Skip()
        
    def __on_import_menu(self, event):
        dbimport = edimport.EDImportDialog(self, wx.ID_ANY, "Import Exploration Database")
        
        if dbimport.ShowModal() == wx.ID_OK:
            print "OK"
            
        dbimport.Destroy()
        
    def __on_pref_menu(self, event):
        settings = edsettings.EDSettings(self, wx.ID_ANY, "Settings Configuration")
        
        if settings.ShowModal() == wx.ID_OK:
            if self.stop_button.IsEnabled():
                self.log.info("The preferences have changed. Stop the proxy and then attempt to restart it.")
                
                self.stop_button.Disable()
                self.__stop()
                self.start_button.Enable()
                
                wx.PostEvent(self.GetEventHandler(), wx.PyCommandEvent(wx.EVT_BUTTON.typeId, self.start_button.GetId()))
            
        settings.Destroy()
    
    def __on_exit_menu(self, event):
        self.__stop()
        edsmdb.get_instance().close()
        self.Destroy()
        
    def __new_client_thread(self, client, addr):
        while not client.is_initialized() and client.is_running():
            try:
                client.wait_for_initialized(0.5)
            except ednet.TimeoutException:
                self.log.debug("Timeout waiting for initialized. Try again.")

        try:
            self._lock.acquire()
            self.client_listview.Append([ addr[0], addr[1] ])
            self._client_list.append(client)
            
            client.set_ondisconnect_listener(self.__on_client_disconnect)
            client.set_onrecv_listener(self.__on_net_recv)
        finally:
            self._lock.release()

        if client.get_start_time() is not None:
            edparser.parse_past_logs(self._edconfig.get_netlog_path(),
                                     self._netlog_parser.get_netlog_prefix(),
                                     self.__on_sync_parser_event,
                                     args = (client,),
                                     start_time = client.get_start_time())

            edparser.parse_past_journals(self._edconfig.get_journal_path(),
                            self._journal_parser.get_journal_prefix(),
                            self.__on_sync_parser_event,
                            args = (client,),
                            start_time = client.get_start_time())

        event = edsmdb.StarMapDbUpdatedEvent()
        client.send(event)

    def __on_async_parser_event(self, event):
        if event.get_line_type() == netlogline.NETLOG_LINE_TYPE.SYSTEM:
            self._edpicture.set_name_replacement(event.get_name())
            self._edconfig.set_image_name_replacement(event.get_name())
               
        try:
            self.log.debug("Sending new event: [%s]", event) 
            self._lock.acquire()
            for client in self._client_list:
                client.send(event)
                
            for plugin in self._plugin_operational_list:
                index = self.plugin_listview.FindItem(0, plugin.get_name())
                
                if index != -1:
                    self.plugin_listview.SetStringItem(index, 1, "Transmitting...")
                    
                plugin.post(event)

                if index != -1:
                    self.plugin_listview.SetStringItem(index, 1, "Waiting for data...")
        finally:
            self._lock.release()

    def __on_sync_parser_event(self, event, client):
        if event.get_line_type() == netlogline.NETLOG_LINE_TYPE.SYSTEM:
            self._edpicture.set_name_replacement(event.get_name())
            self._edconfig.set_image_name_replacement(event.get_name())

        client.send(event)

    def __on_new_client(self, client, addr):
        self.log.info("New remote client at [%s] connected", addr)
        
#         try:
#             self._lock.acquire()
# #             for _client in self._client_list:
# #                 if _client.get_peername()[0] == client.get_peername()[0]:
# #                     self.log.debug("remote client in list close: [%s]", _client.get_peername())
# #                     _client.close()
# #                     self.log.debug("Done with close")
#         finally:
#             self.log.debug("Good to go with the new client.")
#             self._lock.release()

        _thread = threading.Thread(target = self.__new_client_thread, args = (client, addr))
        _thread.daemon = True
        _thread.start()

    def __on_client_disconnect(self, client):
        try:
            peername = client.get_peername()
            self.log.info("Disconnecting [%s]", peername)
            
            self.log.debug("1")
            self._lock.acquire()
            self.log.debug("2")
            self._client_list.remove(client)
            self.log.debug("3")
            
            index = self.client_listview.FindItem(0, peername[0])
            self.log.debug("4")
            if index != -1:
                self.log.debug("5 [%d]" % index)
                self.client_listview.DeleteItem(index)
                wx.SafeYield()
            self.log.debug("6")
        finally:
            self.log.debug("Disconnect done.")
            self._lock.release()
        
    def __on_net_recv(self, event):
#         self.log.debug("New net event: [%s]", str(event))
        if event.get_line_type() == 'SendKeys':
            edsendkeys.sendkeys(event.get_keys())
        elif event.get_line_type() == 'GetDistances':
#             self.log.debug("New distance event: [%s]", str(event))
            dist_response = ednet.StarMapDistanceResponseEvent()
            edsm = edsmdb.get_instance()
            
            for dist in event.get_distances():
                distance = edsm.get_distance(dist['sys1'], dist['sys2'])
                
                if distance and distance.distance != 0.0:
                    dist_response.add(dist['sys1'], dist['sys2'], distance.distance)
                
            self.log.debug("Get Dist Response: [%s]" % str(dist_response))
            event.get_proxy_client().send(dist_response)
        
    def __on_new_message(self, message):
        if message.get_type() == ednet.DISCOVERY_SERVICE_TYPE.QUERY:
            self.log.debug("Received new discovery query message [%s]", message)
            if not message.get_name() or message.get_name() == 'edproxy':
                self._discovery_service.send(ednet.EDDiscoveryMessageAnnounce('edproxy',
                                                                              edutils.get_ipaddr(),
                                                                              45550))

    def __on_new_image(self, event):
        self.log.debug("Received new image: [%s]", event)
        
        try:
            self._lock.acquire()
            for client in self._client_list:
                self.log.debug("Send image to: [%s]", client.get_peername())
                client.send(event)
        finally:
            self._lock.release()

    def __plugin_sync_parser_event(self, event, plugin):
        plugin.post(event)
        
    def __plugin_thread(self, plugin):
        self.log.debug("New Plugin (EDSM) has been added.")
        index = self.plugin_listview.Append([ plugin.get_name(), "Transmitting..." ])
        self.log.debug("Parse old logs.")

        # We need to parse old logs twice because it takes so long we may have missed
        # a couple of systems at the end since the user is not going to wait for it.
        #
        # The first time is to pick up all systems. This may take a VERY long time
        # initial log upload. (30+ minutes)
        # The second time is to pick up any systems that were jumped to while
        # transmitting the initial set. If This is NOT an initial upload then
        # this will be very close to, or exactly, a no-op due to start time.
        # The third time should absolutely be a no-op, but is there to 
        # just make sure we got everything.
        for _ in range(3):
            edparser.parse_past_logs(self._edconfig.get_netlog_path(),
                                     self._netlog_parser.get_netlog_prefix(),
                                     self.__plugin_sync_parser_event,
                                     args = (plugin,),
                                     start_time = plugin.get_last_interaction_time())
        self.log.debug("Done parse old logs.")
        self.plugin_listview.SetStringItem(index, 1, "Waiting for data...")
        
        try:
            self._lock.acquire()
            self._plugin_operational_list.append(plugin)
        finally:
            self._lock.release()


    def on_start(self, event):  # wxGlade: EDProxyFrame.<event_handler>
        netlog_path = self._edconfig.get_netlog_path()
        journal_path = self._edconfig.get_journal_path()

        appconfig_path = os.path.join(self._edconfig.get_appconfig_path(), "AppConfig.xml")
#         appconfig_path = os.path.join(self._edconfig.get_appconfig_path(), "AppConfigLocal.xml")
        
        if not netlog_path or not os.path.exists(netlog_path):
            msg = wx.MessageDialog(parent = self,
                       message = "Error: Invalid log path specified!",
                       caption = "Error starting proxy server",
                       style = wx.OK | wx.ICON_ERROR)
            msg.ShowModal()
            msg.Destroy()
        elif not appconfig_path or not os.path.exists(appconfig_path):
            msg = wx.MessageDialog(parent = self,
                                   message = "Error: Cannot find E:D configuration file!",
                                   caption = "Error starting proxy server",
                                   style = wx.OK | wx.ICON_ERROR)
            msg.ShowModal()
            msg.Destroy()
        else:
            self.start_button.Disable()

            edsm_db = edsmdb.get_instance()
            edsm_db.connect()

            if edsm_db.is_install_required():
                self._edsm_progress_dialog = wx.ProgressDialog("Synchronizing EDSM Database", "Synchronizing EDSM Database...", parent = self)
                self._edsm_progress_dialog.SetSize((480, 103))
                self._edsm_progress_dialog.Center()
    
                edsm_db.install_edsmdb(onprogress=self.__edsm_on_progress)
    
                self._edsm_progress_dialog.Destroy()
                wx.SafeYield()

            edsm_db.start_background_update(onupdate = self.__edsm_on_update)

            try:
                self._netlog_parser.set_netlog_prefix(edutils.get_logfile_prefix(appconfig_path))
                self._journal_parser.set_journal_prefix('Journal')
                
                if os.path.exists(self._edconfig.get_image_path()):
                    self._edpicture.set_image_path(self._edconfig.get_image_path())
                    self._edpicture.set_convert_format(self._edconfig.get_image_format())
                    self._edpicture.set_delete_after_convert(self._edconfig.get_image_delete_after_convert())
                    self._edpicture.set_convert_space(self._edconfig.get_image_convert_space())
                    self._edpicture.set_name_replacement(self._edconfig.get_image_name_replacement())
                    
                    self._edpicture.start()
                    
                self._netlog_parser.start(netlog_path)
                self._journal_parser.start(journal_path)
                
                self.log.debug("Starting up plugins.")
                for value in self._plugin_list:
                    self.log.debug("Plugin %s:%s", value.get_name(), str(value.is_operational()))
                    if value.is_operational():
                        _thread = threading.Thread(target = self.__plugin_thread, args = (value,))
                        _thread.daemon = True
                        _thread.start()
                self.log.debug("Done plugins")
                
                self._proxy_server.start()
                self._websocket_server.start()
                self._discovery_service.start()

                # Announce to the world that EDProxy is up and running.
                self._discovery_service.send(ednet.EDDiscoveryMessageAnnounce('edproxy', edutils.get_ipaddr(), 45550))

#                     self._import_menu.Enable(True)
                self.stop_button.Enable()
            except:
                self.log.error("There was an error starting the proxy.", exc_info = sys.exc_info())
                
                self.stop_button.Disable()

                self._discovery_service.stop()
                self._proxy_server.stop()
                self._websocket_server.stop()
                self._edpicture.stop()
                self._netlog_parser.stop()

                self.start_button.Enable()

                edsm_db.close()
                
                msg = wx.MessageDialog(parent = self,
                                       message = "Error starting up proxy server. Super generic error huh!? Welp, not really going to do better right now. Lazy, lazy, lazy.",
                                       caption = "Error starting proxy server",
                                       style = wx.OK | wx.ICON_ERROR)
                msg.ShowModal()
                msg.Destroy()
            
        event.Skip()

    def on_stop(self, event):  # wxGlade: EDProxyFrame.<event_handler>
        self._import_menu.Enable(False)
        self.stop_button.Disable()
        self.__stop()
        self.start_button.Enable()

        event.Skip()

    def on_win_close(self, event):
        self.__stop()

        event.Skip()

# end of class EDProxyFrame
class EDProxyApp(wx.App):
    def OnInit(self):
        wx.InitAllImageHandlers()
        ed_frame = EDProxyFrame(None, wx.ID_ANY, "")
        self.SetTopWindow(ed_frame)
        ed_frame.Show()
        return 1

# end of class EDProxyApp

class LoggerWriter(object):
    def __init__(self, logger, log_level = logging.INFO):
        self._logger = logger
        self._log_level = log_level
        
    def write(self, buf):
        if buf and buf.rstrip():
            self._logger.log(self._log_level, buf.rstrip())
        
if __name__ == "__main__":
    gettext.install("edproxy") # replace with the appropriate catalog name
    
    user_dir = os.path.join(edutils.get_user_dir(), ".edproxy")
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
        
    user_dir = os.path.join(user_dir, "edproxy.log")
    # logging.basicConfig(format = "%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d    %(message)s", filename = user_dir)
    
    root_log_handler = logging.handlers.RotatingFileHandler(user_dir, maxBytes=(2 * 1024 * 1024), backupCount=5)
    root_log_handler.setFormatter(logging.Formatter("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d    %(message)s"))
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(root_log_handler)

    sys.stdout = LoggerWriter(root_logger, logging.INFO)
    sys.stderr = LoggerWriter(root_logger, logging.ERROR)

    edproxy = EDProxyApp(0)
    edproxy.MainLoop()
