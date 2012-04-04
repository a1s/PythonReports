"""Toolbars for editor"""
"""
04-apr-2012 [kacah]    created

"""
import wx
import wx.lib.agw.aui as wxaui

import utils

class FileToolbar(wxaui.AuiToolBar):
    """ToolBar for file operations - Open, Save, New"""

    def __init__(self, parent):
        wxaui.AuiToolBar.__init__(self, parent, wx.ID_ANY,
            agwStyle=wxaui.AUI_TB_DEFAULT_STYLE)
        self.SetToolBitmapSize(wx.Size(24, 24))

        self.AddSimpleTool(1, "New template", utils.get_icon("new.png"))
        self.AddSimpleTool(2, "Open template", utils.get_icon("open.png"))
        self.AddSimpleTool(3, "Save template", utils.get_icon("save.png"))

        self.Realize()

class VisualToolbar(wxaui.AuiToolBar):
    """ToolBar for new visual elements creation"""

    def __init__(self, parent):
        wxaui.AuiToolBar.__init__(self, parent, wx.ID_ANY,
            agwStyle=wxaui.AUI_TB_DEFAULT_STYLE)
        self.SetToolBitmapSize(wx.Size(24, 24))

        self.AddSimpleTool(1, "Create field", utils.get_icon("field.png"))
        self.AddSimpleTool(2, "Create line", utils.get_icon("line.png"))
        self.AddSimpleTool(3, "Create rectangle", utils.get_icon("rect.png"))
        self.AddSimpleTool(4, "Create image", utils.get_icon("image.png"))
        self.AddSimpleTool(5, "Create barcode", utils.get_icon("barcode.png"))

        self.Realize()
