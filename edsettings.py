import wx
import edconfig
import edpicture
import edutils
import os

format_selector = {
    0: edpicture.IMAGE_CONVERT_FORMAT.BMP,
    1: edpicture.IMAGE_CONVERT_FORMAT.PNG,
    2: edpicture.IMAGE_CONVERT_FORMAT.JPG,
    wx.NOT_FOUND: edpicture.IMAGE_CONVERT_FORMAT.BMP
}

space_selector = {
    0: '',
    1: '_',
    2: '-',
    3: '.',
    wx.NOT_FOUND: ''
}


class EDSettings(wx.Dialog):
    def __init__(self, *args, **kwargs):
        wx.Dialog.__init__(self, *args, **kwargs)
        
        self._edconfig = edconfig.get_instance()
        
        self._start_on_launch = wx.CheckBox(self, label = "Start proxy on Edproxy launch")
        self._start_on_startup = wx.CheckBox(self, label = "Start Edproxy on system startup")
        self._start_minimized = wx.CheckBox(self, label = "Start Edproxy minimized")
        
        self._netlog_path = wx.TextCtrl(self) #, wx.ID_ANY, _(self._edconfig.get_netlog_path()))
        self._netlog_browse_button = wx.Button(self, wx.ID_ANY, _("Browse"))

        self._image_path = wx.TextCtrl(self) #, wx.ID_ANY, _(self._edconfig.get_image_path()))
        self._image_browse_button = wx.Button(self, wx.ID_ANY, _("Browse"))

        self._image_delete = wx.CheckBox(self, label = "Delete original after conversion")
        self._image_format = wx.Choice(self, choices = [ edpicture.IMAGE_CONVERT_FORMAT.BMP, edpicture.IMAGE_CONVERT_FORMAT.PNG, edpicture.IMAGE_CONVERT_FORMAT.JPG ])
        self._image_replace = wx.Choice(self, choices = [ "Keep Space", "Underscore", "Hyphen", "Period" ])

        self._netlog_path.SetMinSize((467, 29))
        self._image_path.SetMinSize((467, 29))
        
        self.Bind(wx.EVT_BUTTON, self.__on_ok, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.__on_netlog_browse, self._netlog_browse_button)
        self.Bind(wx.EVT_BUTTON, self.__on_image_browse, self._image_browse_button)
    
        self.__do_defaults()    
        self.__do_layout()
        
    def __do_defaults(self):
        self._start_on_launch.SetValue(self._edconfig.get_edproxy_startup())
        self._start_on_startup.SetValue(self._edconfig.get_system_startup())
        self._start_minimized.SetValue(self._edconfig.get_start_minimized())
        
        self._start_on_startup.Disable()
        self._start_minimized.Disable()
        
        self._netlog_path.ChangeValue(self._edconfig.get_netlog_path())
        
        self._image_path.ChangeValue(self._edconfig.get_image_path())
        self._image_delete.SetValue(self._edconfig.get_image_delete_after_convert())
        
        for k, v in format_selector.iteritems():
            if v == self._edconfig.get_image_format() and k != wx.NOT_FOUND:
                self._image_format.SetSelection(k)
                break
        
        for k, v in space_selector.iteritems():
            if v == self._edconfig.get_image_convert_space() and k != wx.NOT_FOUND:
                self._image_replace.SetSelection(k)
                break
    
    def __do_layout(self):
        # The three main panel boxes
        sizer1 = wx.StaticBoxSizer(wx.StaticBox(self, label = "General"), wx.VERTICAL)
        sizer2 = wx.StaticBoxSizer(wx.StaticBox(self, label = "Netlog Configuration"), wx.HORIZONTAL)
        sizer3 = wx.StaticBoxSizer(wx.StaticBox(self, label = "Image Configuraiton"), wx.VERTICAL)
        
        box1 = wx.BoxSizer(wx.VERTICAL)
        box2 = wx.BoxSizer(wx.HORIZONTAL)
        box3 = wx.BoxSizer(wx.HORIZONTAL) 
        box4 = wx.BoxSizer(wx.HORIZONTAL)
        
        button_sizer = self.CreateSeparatedButtonSizer(wx.CANCEL | wx.OK)

        # Add all the main panel boxes to the top-level sizer
        box1.Add(sizer1, 0, wx.EXPAND)
        box1.AddSpacer(5)
        box1.Add(sizer2, 0, wx.EXPAND)
        box1.AddSpacer(5)
        box1.Add(sizer3, 0, wx.EXPAND)
        box1.Add(button_sizer, 0, wx.EXPAND | wx.ALIGN_RIGHT)
        
        sizer1.Add(self._start_on_startup, 0, wx.EXPAND | wx.ALIGN_LEFT)
        sizer1.AddSpacer(5)
        sizer1.Add(self._start_on_launch, 0, wx.EXPAND | wx.ALIGN_LEFT)
        sizer1.AddSpacer(5)
        sizer1.Add(self._start_minimized, 0, wx.EXPAND | wx.ALIGN_LEFT)
        
        sizer2.Add(wx.StaticText(self, wx.ID_ANY, _("Netlog Path:"), style=wx.ST_NO_AUTORESIZE), flag = wx.ALIGN_LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)
        sizer2.AddSpacer(2)
        sizer2.Add(self._netlog_path, 1)
        sizer2.AddSpacer(5)
        sizer2.Add(self._netlog_browse_button, flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)
        
        box2.Add(wx.StaticText(self, wx.ID_ANY, _("Images Path:"), style=wx.ST_NO_AUTORESIZE), flag = wx.ALIGN_LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)
        box2.AddSpacer(2)
        box2.Add(self._image_path, 1)
        box2.AddSpacer(5)
        box2.Add(self._image_browse_button, flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)
        
        box3.Add(self._image_format)
        box3.Add(wx.StaticText(self, wx.ID_ANY, _("Choose the conversion format (.bmp means no conversion)"), style=wx.ST_NO_AUTORESIZE))
        
        box4.Add(self._image_replace)
        box4.Add(wx.StaticText(self, wx.ID_ANY, _("Replace \"space\" with a single character"), style=wx.ST_NO_AUTORESIZE))
        
        sizer3.Add(box2)
        sizer3.AddSpacer(5)
        sizer3.Add(box3)
        sizer3.AddSpacer(5)
        sizer3.Add(box4)
        sizer3.AddSpacer(5)
        sizer3.Add(self._image_delete)
        
        self.SetSizer(box1)
        box1.Fit(self)
        self.Layout()
        self.Centre()

    def __on_ok(self, event):
        self._edconfig.set_system_startup(self._start_on_startup.IsChecked())
        self._edconfig.set_edproxy_startup(self._start_on_launch.IsChecked())
        self._edconfig.set_start_minimized(self._start_minimized.IsChecked())
        
        self._edconfig.set_netlog_path(os.path.abspath(os.path.expanduser(self._netlog_path.GetValue())))

        self._edconfig.set_image_path(os.path.abspath(os.path.expanduser(self._image_path.GetValue())))
        self._edconfig.set_image_delete_after_convert(self._image_delete.IsChecked())
        self._edconfig.set_image_format(format_selector[self._image_format.GetSelection()])
        self._edconfig.set_image_convert_space(space_selector[self._image_replace.GetSelection()])
        
        event.Skip()

    def __on_netlog_browse(self, event):
        defpath = self._netlog_path.GetValue()
        
        if len(defpath) == 0:
            defpath = edutils.get_user_dir()
            
        dir_path = wx.DirDialog(self, "Choose Netlog Path", style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST, defaultPath = defpath)

        if dir_path.ShowModal() == wx.ID_OK:
            self._netlog_path.ChangeValue(dir_path.GetPath())
            
        dir_path.Destroy()
        event.Skip()
    
    def __on_image_browse(self, event):
        defpath = self._image_path.GetValue()
        
        if len(defpath) == 0:
            defpath = edutils.get_user_dir()
            
        dir_path = wx.DirDialog(self, "Choose Images Path", style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST, defaultPath = defpath)

        if dir_path.ShowModal() == wx.ID_OK:
            self._image_path.ChangeValue(dir_path.GetPath())
            
        dir_path.Destroy()
        event.Skip()