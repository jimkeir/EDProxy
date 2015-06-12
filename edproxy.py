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

import os
import datetime, time
import threading
import ConfigParser

import edutils
import ednet
import edparser

class EDProxyFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: EDProxyFrame.__init__
        kwds["style"] = wx.CAPTION | wx.CLOSE_BOX | wx.MINIMIZE_BOX | wx.CLIP_CHILDREN
        wx.Frame.__init__(self, *args, **kwds)
        self.label_1 = wx.StaticText(self, wx.ID_ANY, _("Netlog Path:"), style=wx.ST_NO_AUTORESIZE)
        self.netlog_path_txt_ctrl = wx.TextCtrl(self, wx.ID_ANY, _("/home/wes/src/edproxy/logs"))
        self.browse_button = wx.Button(self, wx.ID_ANY, _("Browse"))
        self.start_button = wx.Button(self, wx.ID_ANY, _("Start"))
        self.stop_button = wx.Button(self, wx.ID_ANY, _("Stop"))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_browse, self.browse_button)
        self.Bind(wx.EVT_BUTTON, self.on_start, self.start_button)
        self.Bind(wx.EVT_BUTTON, self.on_stop, self.stop_button)
        # end wxGlade

        self.Bind(wx.EVT_CLOSE, self.on_win_close)
        
        configfilename = os.path.join(edutils.get_app_dir(), "edproxy.ini")
        if os.path.exists(configfilename):
            config = ConfigParser.SafeConfigParser()
            config.read(configfilename)

            value = config.get('Paths', 'netlog')
            
            self.netlog_path_txt_ctrl.ChangeValue(value)
        else:
            config = ConfigParser.SafeConfigParser()
            config.add_section('Paths')
            value = "C:\\Program Files (x86)\\Frontier\\EDLaunch\\Products\\FORC-FDEV-D-1010\\Logs"
            config.set('Paths', 'netlog', value)

            with open(configfilename, 'w') as configfile:
                config.write(configfile)

            self.netlog_path_txt_ctrl.ChangeValue(value)

    def __set_properties(self):
        # begin wxGlade: EDProxyFrame.__set_properties
        self.SetTitle(_("Elite: Dangerous Netlog Proxy"))
        self.netlog_path_txt_ctrl.SetMinSize((467, 29))
        self.stop_button.Enable(False)
        # end wxGlade

        self._lock = threading.Lock()
        self._client_list = list()
        self._netlog_parser = None

        self._discovery_service = ednet.EDDiscoveryService("239.45.99.98", 45551)
        self._discovery_service.add_listener(self.__on_new_message)

        self._proxy_server = ednet.EDProxyServer(45550)
        self._proxy_server.add_listener(self.__on_new_client)

    def __do_layout(self):
        # begin wxGlade: EDProxyFrame.__do_layout
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4.Add(self.label_1, 0, 0, 0)
        sizer_4.Add(self.netlog_path_txt_ctrl, 1, 0, 0)
        sizer_4.Add(self.browse_button, 0, wx.ALIGN_RIGHT, 0)
        sizer_3.Add(sizer_4, 1, wx.EXPAND, 0)
        sizer_5.Add(self.start_button, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_5.Add(self.stop_button, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_3.Add(sizer_5, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.SetSizer(sizer_3)
        sizer_3.Fit(self)
        self.Layout()
        self.Centre()
        # end wxGlade

    def __new_client_thread(self, client, addr):
        while not client.is_initialized():
            client.wait_for_initialized(0.5)

        if client.get_start_time() is not None:
            edparser.EDNetlogParser.parse_past_logs(self.netlog_path_txt_ctrl.GetValue(),
                                                    self._netlog_parser.get_netlog_prefix(),
                                                    self.__on_sync_parser_event,
                                                    args = (client,),
                                                    start_time = client.get_start_time())
        self._lock.acquire()
        self._client_list.append(client)
        self._lock.release()

    def __on_async_parser_event(self, event):
        self._lock.acquire()
        for client in self._client_list:
            client.send(event)
        self._lock.release()

    def __on_sync_parser_event(self, event, client):
        client.send(event)

    def __on_new_client(self, client, addr):
        threading.Thread(target = self.__new_client_thread, args = (client, addr)).start()

    def __on_new_message(self, message):
        if message.get_type() == ednet.DISCOVERY_SERVICE_TYPE.QUERY:
            if not message.get_name() or message.get_name() == 'edproxy':
                self._discovery_service.send(ednet.EDDiscoveryMessageAnnounce('edproxy',
                                                                              edutils.get_ipaddr(),
                                                                              45550))

    def on_browse(self, event):  # wxGlade: EDProxyFrame.<event_handler>
        dir_path = wx.DirDialog(self, "Choose Netlog Path", style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)

        if dir_path.ShowModal() == wx.ID_OK:
            self.netlog_path_txt_ctrl.ChangeValue(dir_path.GetPath())

            configfilename = os.path.join(edutils.get_app_dir(), "edproxy.ini")
            config = ConfigParser.SafeConfigParser()
            config.read(configfilename)
            config.set('Paths', 'netlog', dir_path.GetPath())

            with open(configfilename, 'w') as configfile:
                config.write(configfile)

        dir_path.Destroy()

        event.Skip()

    def on_start(self, event):  # wxGlade: EDProxyFrame.<event_handler>
        netlog_path = self.netlog_path_txt_ctrl.GetValue()
        if netlog_path and os.path.exists(netlog_path):
            self.start_button.Disable()
            self.browse_button.Disable()
            self.netlog_path_txt_ctrl.Disable()

            try:
                config_path, _ = os.path.split(os.path.normpath(netlog_path))
                config_path = os.path.join(config_path, "AppConfig.xml")

                if os.path.exists(config_path):
                    if self._netlog_parser is None:
                        self._netlog_parser = edparser.EDNetlogParser(logfile_prefix = edutils.get_logfile_prefix(config_path))

                        self._netlog_parser.add_listener(self.__on_async_parser_event)

                    if not edutils.is_verbose_enabled(config_path):
                        while edutils.is_ed_running():
                            msg = wx.MessageDialog(parent = self,
                                                   message = "Elite: Dangerous is currently running and Verbose logging will not take effect until Elite: Dangerous is restarted. Please shutdown Elite: Dangerous before continuing.",
                                                   caption = "Verbose Logging Setup Error",
                                                   style = wx.OK | wx.ICON_EXCLAMATIONN)
                            msg.ShowModal()
                            msg.Destroy()

                        edutils.set_verbose_enabled(config_path, True)
                        edutils.set_datestamp_enabled(config_path, True)
 
                    self._netlog_parser.start(netlog_path)
                    self._proxy_server.start()
                    self._discovery_service.start()

                    # Announce to the world that EDProxy is up and running.
                    self._discovery_service.send(ednet.EDDiscoveryMessageAnnounce('edproxy', edutils.get_ipaddr(), 45550))

                    self.stop_button.Enable()
                else:
                    msg = wx.MessageDialog(parent = self,
                                           message = "Error: Cannot find E:D configuration file!",
                                           caption = "Error starting proxy server",
                                           style = wx.OK | wx.ICON_ERROR)
                    msg.ShowModal()
                    msg.Destroy()

                    self.netlog_path_txt_ctrl.Enable()
                    self.browse_button.Enable()
                    self.start_button.Enable()
            except:
                self.stop_button.Disable()

                self._discovery_service.stop()
                self._proxy_server.stop()
                self._netlog_parser.stop()

                self.netlog_path_txt_ctrl.Enable()
                self.browse_button.Enable()
                self.start_button.Enable()

                msg = wx.MessageDialog(parent = self,
                                       message = "Error starting up proxy server. Super generic error huh!? Welp, not really going to do better right now. Lazy, lazy, lazy.",
                                       caption = "Error starting proxy server",
                                       style = wx.OK | wx.ICON_ERROR)
                msg.ShowModal()
                msg.Destroy()
        else:
            msg = wx.MessageDialog(parent = self,
                                   message = "Error: Invalid log path specified!",
                                   caption = "Error starting proxy server",
                                   style = wx.OK | wx.ICON_ERROR)
            msg.ShowModal()
            msg.Destroy()
            
        event.Skip()

    def on_stop(self, event):  # wxGlade: EDProxyFrame.<event_handler>
        self.stop_button.Disable()

        self._discovery_service.stop()
        self._proxy_server.stop()
        self._netlog_parser.stop()

        self._lock.acquire()
        for client in self._client_list:
            client.close()
        self._lock.release()

        self.netlog_path_txt_ctrl.Enable()
        self.browse_button.Enable()
        self.start_button.Enable()

        event.Skip()

    def on_win_close(self, event):
        if self.stop_button.IsEnabled():
            self._discovery_service.stop()
            self._proxy_server.stop()
            self._netlog_parser.stop()

            self._lock.acquire()
            for client in self._client_list:
                client.close()
            self._lock.release()

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

if __name__ == "__main__":
    gettext.install("edproxy") # replace with the appropriate catalog name

    edproxy = EDProxyApp(0)
    edproxy.MainLoop()
