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

        self.AddSimpleTool(1, "New", utils.get_icon("new.png"), "New template")
        self.AddSimpleTool(2, "Open", utils.get_icon("open.png"),
            "Open template")
        self.AddSimpleTool(3, "Save", utils.get_icon("save.png"),
            "Save template")

        self.Realize()

class VisualToolbar(wxaui.AuiToolBar):
    """ToolBar for new visual elements creation"""

    def __init__(self, parent):
        wxaui.AuiToolBar.__init__(self, parent, wx.ID_ANY,
            agwStyle=wxaui.AUI_TB_DEFAULT_STYLE)
        self.SetToolBitmapSize(wx.Size(24, 24))

        self.AddSimpleTool(1, "Arrow", utils.get_icon("arrow.png"),
            "Select elements")
        self.AddSeparator()
        self.AddSimpleTool(2, "Field", utils.get_icon("field.png"),
            "Create field")
        self.AddSimpleTool(3, "Line", utils.get_icon("line.png"),
            "Create line")
        self.AddSimpleTool(4, "Rectangle", utils.get_icon("rect.png"),
            "Create rectangle")
        self.AddSimpleTool(5, "Image", utils.get_icon("image.png"),
            "Create image")
        self.AddSimpleTool(6, "Barcode", utils.get_icon("barcode.png"),
            "Create barcode")

        self.Realize()
