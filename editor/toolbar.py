"""Toolbars for editor"""
"""
04-apr-2012 [kacah]    created

"""
import wx
import wx.lib.agw.aui as wxaui

from elements.design import DESIGN_TOOLS
import utils

class FileToolbar(wxaui.AuiToolBar):
    """ToolBar for file operations - Open, Save, New"""

    TOOLS = [
        (1, "New", "new.png", "New template", "self.OnNew"),
        (2, "Open", "open.png", "Open template", "self.OnOpen"),
        (3, "Save", "save.png", "Save template", "self.OnSave"),
    ]

    def __init__(self, parent):
        wxaui.AuiToolBar.__init__(self, parent, wx.ID_ANY,
            agwStyle=wxaui.AUI_TB_DEFAULT_STYLE)
        self.SetToolBitmapSize(wx.Size(24, 24))

        for _tool in self.TOOLS:
            _icon = utils.get_icon(_tool[2])
            self.AddSimpleTool(_tool[0], _tool[1], _icon, _tool[3])
            self.Bind(wx.EVT_TOOL, eval(_tool[4]), id=_tool[0])

        self.Realize()

    def OnNew(self, evt):
        wx.GetApp().report_new()

    def OnOpen(self, evt):
        pass

    def OnSave(self, evt):
        pass


class VisualToolbar(wxaui.AuiToolBar):
    """ToolBar for new visual elements creation"""

    TOOLS = [
        (DESIGN_TOOLS["Select"], "arrow", "arrow.png", "Select elements"),
        (DESIGN_TOOLS["Field"], "field", "field.png", "Create field"),
        (DESIGN_TOOLS["Line"], "Line", "line.png", "Create line"),
        (DESIGN_TOOLS["Rectangle"], "Rectangle", "rect.png", "Create rectangle"),
        (DESIGN_TOOLS["Image"], "Image", "image.png", "Create image"),
        (DESIGN_TOOLS["Barcode"], "Barcode", "barcode.png", "Create barcode"),
    ]

    def __init__(self, parent):
        wxaui.AuiToolBar.__init__(self, parent, wx.ID_ANY,
            agwStyle=wxaui.AUI_TB_DEFAULT_STYLE)
        self.SetToolBitmapSize(wx.Size(24, 24))

        for _tool in self.TOOLS:
            _icon = utils.get_icon(_tool[2])
            self.AddRadioTool(_tool[0].id, _tool[1], _icon, _icon, _tool[3])

        self.Realize()

        self.ToggleTool(DESIGN_TOOLS["Select"].id, True)

    def get_selected_tool(self):
        """Return selected tool id"""

        for _tool in self.TOOLS:
            if self.GetToolToggled(_tool[0].id):
                return _tool[0]
