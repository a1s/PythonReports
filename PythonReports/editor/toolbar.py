"""Toolbars for editor"""

import wx
import wx.lib.agw.aui as wxaui

from elements.design import DESIGN_TOOLS
import utils

class FileToolbar(wxaui.AuiToolBar):
    """ToolBar for file operations - Open, Save, New"""

    TOOLS = [
        (1, "New", "glyphicons_036_file", "New template", "self.OnNew"),
        (2, "Open", "glyphicons_359_file_export", "Open template",
            "self.OnOpen"),
        (3, "Save", "glyphicons_358_file_import", "Save template",
            "self.OnSave"),
    ]

    def __init__(self, parent):
        wxaui.AuiToolBar.__init__(self, parent, wx.ID_ANY,
            agwStyle=wxaui.AUI_TB_DEFAULT_STYLE)
        self.SetToolBitmapSize(wx.Size(24, 24))

        self.app = wx.GetApp()

        for _tool in self.TOOLS:
            _icon = utils.get_icon(_tool[2])
            self.AddSimpleTool(_tool[0], _tool[1], _icon, _tool[3])
            self.Bind(wx.EVT_TOOL, eval(_tool[4]), id=_tool[0])

        self.Realize()

    def OnNew(self, evt):
        self.app.report_new()

    def OnOpen(self, evt):
        self.app.report_open()

    def OnSave(self, evt):
        self.app.report_save()


class VisualToolbar(wxaui.AuiToolBar):
    """ToolBar for new visual elements creation"""

    TOOLS = [
        (DESIGN_TOOLS["Select"], "Select",
            "glyphicons_099_vector_path_all", "Select elements"),
        (DESIGN_TOOLS["Field"], "Field",
            "glyphicons_104_text", "Create field"),
        (DESIGN_TOOLS["Line"], "Line",
            "glyphicons_097_vector_path_line", "Create line"),
        (DESIGN_TOOLS["Rectangle"], "Rectangle",
            "glyphicons_094_vector_path_square", "Create rectangle"),
        (DESIGN_TOOLS["Image"], "Image",
            "glyphicons_159_picture", "Create image"),
        (DESIGN_TOOLS["Barcode"], "Barcode",
            "glyphicons_259_barcode", "Create barcode"),
    ]

    def __init__(self, parent):
        wxaui.AuiToolBar.__init__(self, parent, wx.ID_ANY,
            agwStyle=wxaui.AUI_TB_DEFAULT_STYLE)
        self.SetToolBitmapSize(wx.Size(24, 24))

        for _tool in self.TOOLS:
            _icon = utils.get_icon(_tool[2])
            self.AddRadioTool(_tool[0].id, _tool[1], _icon, _icon, _tool[3])

        self.Realize()

        self.set_selected_tool(DESIGN_TOOLS["Select"])

    def get_selected_tool(self):
        """Return selected tool id"""

        for _tool in self.TOOLS:
            if self.GetToolToggled(_tool[0].id):
                return _tool[0]

    def set_selected_tool(self, design_tool):
        """Set selected design tool"""

        self.ToggleTool(design_tool.id, True)
        self.Refresh()

# vim: set et sts=4 sw=4 :
