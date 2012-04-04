"""Main frame of editor"""
"""
20-mar-2012 [kacah]   created

"""
import wx
import wx.lib.agw.aui as wxaui
import wx.py as wxpy

from propertiesgrid import PropertiesGrid
from toolbar import FileToolbar, VisualToolbar
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

        self.property_grid = PropertiesGrid(self)
        self.shell = wxpy.shell.Shell(self, wx.ID_ANY, wx.DefaultPosition,
            wx.Size(200, 150), wx.NO_BORDER, introText=INTRO_TEXT)
        self.workspace = Workspace(self, self.property_grid)
        self.file_toolbar = FileToolbar(self)
        self.visual_toolbar = VisualToolbar(self)

        self.aui_mgr.AddPane(self.property_grid, wx.RIGHT, "Properties")
        self.aui_mgr.AddPane(self.shell, wx.BOTTOM, "Shell")
        self.aui_mgr.AddPane(self.workspace, wx.CENTER)
        self.aui_mgr.AddPane(self.file_toolbar, wxaui.AuiPaneInfo().Name
			("File toolbar").Caption("").ToolbarPane().Top())
        self.aui_mgr.AddPane(self.visual_toolbar, wxaui.AuiPaneInfo().Name
            ("Visual toolbar").Caption("").ToolbarPane().Top())

        menuBar = wx.MenuBar()
        fileMenu = wx.Menu()
        exitMenuItem = fileMenu.Append(wx.NewId(), "Exit", "Exit the application")
        menuBar.Append(fileMenu, "&File")
        self.SetMenuBar(menuBar)

        self.aui_mgr.Update()

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event):
        self.aui_mgr.UnInit()
        self.Destroy()
