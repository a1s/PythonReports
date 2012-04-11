"""Toolbars for editor"""
"""
04-apr-2012 [kacah]    created

"""
import wx
import wx.lib.agw.aui as wxaui

import environment as env
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

    TOOLS = [
        [env.EditingTools.select, "arrow", "arrow.png", "Select elements"],
        [env.EditingTools.field, "field", "field.png", "Create field"],
        [env.EditingTools.line, "Line", "line.png", "Create line"],
        [env.EditingTools.rect, "Rectangle", "rect.png", "Create rectangle"],
        [env.EditingTools.image, "Image", "image.png", "Create image"],
        [env.EditingTools.barcode, "Barcode", "barcode.png", "Create barcode"],
    ]

    def __init__(self, parent):
        wxaui.AuiToolBar.__init__(self, parent, wx.ID_ANY,
            agwStyle=wxaui.AUI_TB_DEFAULT_STYLE)
        self.SetToolBitmapSize(wx.Size(24, 24))

        for _tool in self.TOOLS:
            _icon = utils.get_icon(_tool[2])
            self.AddRadioTool(_tool[0], _tool[1], _icon, _icon, _tool[3])

        self.Realize()

        self.ToggleTool(env.EditingTools.select, True)

    def get_selected_tool(self):
        """Return selected tool id"""

        for _tool in self.TOOLS:
            if self.GetToolToggled(_tool[0]):
                return _tool[0]
