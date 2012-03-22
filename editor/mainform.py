"""Main frame of editor"""
"""
20-mar-2012 [kacah]   created

"""
import wx.py as wxpy
import wx.aui

from propertiesgrid import PropertiesGrid
from workspace import Workspace

FORM_TITLE = "PythonReports editor"
INTRO_TEXT = "Welcome to PythonReports editor"

class EditorForm(wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title=FORM_TITLE,
            pos=wx.DefaultPosition, size=wx.Size(800, 600),
            style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)

        self.aui_mgr = wx.aui.AuiManager(self)

        self.property_grid = PropertiesGrid(self)
        self.shell = wxpy.shell.Shell(self, wx.ID_ANY, wx.DefaultPosition,
            wx.Size(200, 150), wx.NO_BORDER, introText=INTRO_TEXT)
        self.workspace = Workspace(self, self.property_grid)

        self.aui_mgr.AddPane(self.property_grid, wx.RIGHT, "Properties")
        self.aui_mgr.AddPane(self.shell, wx.BOTTOM, "Shell")
        self.aui_mgr.AddPane(self.workspace, wx.CENTER)

        tb1 = wx.ToolBar(self, -1, style=wx.TB_HORIZONTAL | wx.NO_BORDER)
        tb1.AddSimpleTool(1,
			wx.Image("res/save.png", wx.BITMAP_TYPE_PNG).ConvertToBitmap(),
			"Test", "")
        tb1.AddSimpleTool(1,
			wx.Image("res/new.png", wx.BITMAP_TYPE_PNG).ConvertToBitmap(),
			"Test2", "")
        tb1.Realize()
        self.aui_mgr.AddPane(tb1, wx.aui.AuiPaneInfo().Name
			("Toolbar").Caption("").ToolbarPane().Top())

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
