import wx
import edconfig
import edutils

db_path_selector = {
    0: "C:\\Program Files (x86)\\EDDiscovery",
    wx.NOT_FOUND: "C:\\Program Files (x86)\\EDDiscovery"
}

class EDImportDialog(wx.Dialog):
    def __init__(self, *args, **kwargs):
        wx.Dialog.__init__(self, *args, **kwargs)
        
        self._edconfig = edconfig.get_instance()
        
        self._import_path = wx.TextCtrl(self)
        self._import_browse_button = wx.Button(self, wx.ID_ANY, _("Browse"))

        self._import_db = wx.Choice(self, choices = [ "EDDiscovery" ])

        self._import_path.SetMinSize((467, 29))
        self._import_path.ChangeValue(db_path_selector[self._import_db.GetSelection()])
        
        self.Bind(wx.EVT_BUTTON, self.__on_ok, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.__on_import_browse, self._import_browse_button)
    
        self.__do_layout()
        
    def __do_layout(self):
        box1 = wx.BoxSizer(wx.VERTICAL)
        box2 = wx.BoxSizer(wx.HORIZONTAL)
        
        button_sizer = self.CreateSeparatedButtonSizer(wx.CANCEL | wx.OK)

        # Add all the main panel boxes to the top-level sizer
        box1.AddSpacer(10)
        box1.Add(box2, 0, wx.EXPAND)
        box1.Add(button_sizer, 0, wx.EXPAND | wx.ALIGN_RIGHT)
        
        box2.Add(self._import_db, 0, flag = wx.ALIGN_LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)
        box2.AddSpacer(5)
        box2.Add(self._import_path, 1)
        box2.AddSpacer(5)
        box2.Add(self._import_browse_button, flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)
                
        self.SetSizer(box1)
        box1.Fit(self)
        self.Layout()
        self.Centre()

    def __on_ok(self, event):
        event.Skip()

    def __on_import_browse(self, event):
        defpath = self._import_path.GetValue()
        
        if len(defpath) == 0:
            defpath = edutils.get_user_dir()
            
        dir_path = wx.DirDialog(self, "Choose Netlog Path", style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST, defaultPath = defpath)

        if dir_path.ShowModal() == wx.ID_OK:
            self._import_path.ChangeValue(dir_path.GetPath())
            
        dir_path.Destroy()
        event.Skip()
    