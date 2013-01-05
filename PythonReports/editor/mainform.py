"""Main frame of editor"""
"""
17-jun-2012 [als]   Add frame icon
16-jun-2012 [als]   New pane icons based on Glyphicons
20-mar-2012 [kacah] created
"""

import os

import wx
import wx.lib.agw.aui as wxaui
import wx.lib.ogl as wxogl
import wx.py as wxpy

from elementstree import ElementsTree
from mainmenu import MainMenu
from propertiesgrid import PropertiesGrid
from toolbar import FileToolbar, VisualToolbar
import utils
from workspace import Workspace

FORM_TITLE = "PythonReports Template Editor"
INTRO_TEXT = "Welcome to PythonReports Template Editor"

class EditorForm(wx.Frame):
    """Main frame of editor"""

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title=FORM_TITLE,
            pos=wx.DefaultPosition, size=wx.Size(800, 600),
            style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)
        _icon = wx.IconBundle()
        _icon.AddIcon(utils.get_resource_ico("pythonreports"))
        self.SetIcons(_icon)

        wxogl.OGLInitialize()

        self.aui_mgr = wxaui.AuiManager(self)
        self.setup_aui()

        self.create_windows()

        self.main_menu = MainMenu(self)
        self.SetMenuBar(self.main_menu)

        self.aui_mgr.Update()

        self.bind_events()

    def setup_aui(self):
        """Setup flags to AUI manager"""

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
        self.elements_tree = ElementsTree(self)

        self.aui_mgr.AddPane(self.shell, wxaui.AuiPaneInfo()
            .Name("Shell").Caption("Shell").Bottom()
            .CloseButton(False).MinimizeButton(True)
            .Icon(utils.get_icon("img_137_computer_service")))

        self.aui_mgr.AddPane(self.property_grid, wxaui.AuiPaneInfo()
            .Name("PropGrid").Caption("Properties").Right()
            .CloseButton(False).MinimizeButton(True)
            .Icon(utils.get_icon("properties")))

        self.aui_mgr.AddPane(self.elements_tree, wxaui.AuiPaneInfo()
            .Name("ElemTree").Caption("Elements").Left()
            .CloseButton(False).MinimizeButton(True)
            .Icon(utils.get_icon("img_114_list")))

        self.aui_mgr.AddPane(self.workspace, wx.CENTER)
        self.aui_mgr.AddPane(self.file_toolbar, wxaui.AuiPaneInfo().Name
            ("File toolbar").Caption("").ToolbarPane().Top())
        self.aui_mgr.AddPane(self.visual_toolbar, wxaui.AuiPaneInfo().Name
            ("Visual toolbar").Caption("").ToolbarPane().Top())

    def bind_events(self):
        """Bind events to this frame"""

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event=None):
        _dlg = wx.MessageDialog(self,
            "Do you really want to close PythonReports editor?",
            "Confirm Exit", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
        _dlg_result = _dlg.ShowModal()
        _dlg.Destroy()

        if _dlg_result == wx.ID_OK:
            self.aui_mgr.UnInit()
            wxogl.OGLCleanUp()
            self.Destroy()

# vim: set et sts=4 sw=4 :
