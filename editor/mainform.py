"""Main frame of editor"""
"""
20-mar-2012 [kacah]   created

"""
import wx
import wx.lib.agw.aui as wxaui
import wx.py as wxpy

import environment as env
from propertiesgrid import PropertiesGrid
from toolbar import FileToolbar, VisualToolbar
import utils
from workspace import Workspace

FORM_TITLE = "PythonReports editor"
INTRO_TEXT = "Welcome to PythonReports editor"

class EditorForm(wx.Frame):
    """Main frame of editor"""

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title=FORM_TITLE,
            pos=wx.DefaultPosition, size=wx.Size(800, 600),
            style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)

        self.aui_mgr = wxaui.AuiManager(self)
        self.setup_aui()

        self.create_windows()
        env.setup_environment(self.workspace, self.property_grid, self.shell,
            self.file_toolbar, self.visual_toolbar)
        self.workspace.create_new_report()

        menuBar = wx.MenuBar()
        fileMenu = wx.Menu()
        exitMenuItem = fileMenu.Append(wx.NewId(), "Exit", "Exit the application")
        menuBar.Append(fileMenu, "&File")
        self.SetMenuBar(menuBar)

        self.aui_mgr.Update()

        self.bind_events()

    def setup_aui(self):
        """Setup flags fro AUI manager"""

        _agw_flags = self.aui_mgr.GetAGWFlags()
        _agw_flags = _agw_flags ^ \
            wxaui.AUI_MGR_TRANSPARENT_DRAG ^ \
            wxaui.AUI_MGR_SMOOTH_DOCKING
        self.aui_mgr.SetAGWFlags(_agw_flags)

    def create_windows(self):
        """Create all working windows for frame"""

        self.workspace = Workspace(self)
        self.property_grid = PropertiesGrid(self)
        self.shell = wxpy.shell.Shell(self, wx.ID_ANY, wx.DefaultPosition,
            wx.Size(200, 150), wx.NO_BORDER, introText=INTRO_TEXT)
        self.file_toolbar = FileToolbar(self)
        self.visual_toolbar = VisualToolbar(self)

        self.aui_mgr.AddPane(self.shell, wxaui.AuiPaneInfo()
            .Name("Shell").Caption("Shell").Bottom()
            .CloseButton(True).MinimizeButton(True)
            .Icon(utils.get_icon("shell.png")))

        self.aui_mgr.AddPane(self.property_grid, wxaui.AuiPaneInfo()
            .Name("PropGrid").Caption("Properties").Right()
            .CloseButton(True).MinimizeButton(True)
            .Icon(utils.get_icon("properties.png")))

        self.aui_mgr.AddPane(self.workspace, wx.CENTER)
        self.aui_mgr.AddPane(self.file_toolbar, wxaui.AuiPaneInfo().Name
            ("File toolbar").Caption("").ToolbarPane().Top())
        self.aui_mgr.AddPane(self.visual_toolbar, wxaui.AuiPaneInfo().Name
            ("Visual toolbar").Caption("").ToolbarPane().Top())

    def bind_events(self):
        """Bind events to this frame"""

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event):
        self.aui_mgr.UnInit()
        self.Destroy()
