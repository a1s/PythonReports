"""Contain global application objects and data. Link objects."""
"""
04-apr-2012 [kacah]    created

"""
import wx

from mainform import EditorForm
import utils

class EditorApplication(wx.App):
    """Main class, environment of editor"""

    def __init_(self):
        wx.App.__init__(self)

        #disable logs to prevent automatic error windows
        wx.Log.EnableLogging(False)

    def OnInit(self):
        utils.setup()

        self.frame = EditorForm(None)
        self.SetTopWindow(self.frame)
        self.frame.Show()
        self.frame.Maximize(True)

        self.last_focus = None
        return True

    def OnPropertyListener(self, listener):
        """Unfocus last element, focus new, update properties in prop grid"""

        self.remove_focus()
        listener.highlight(True)
        self.frame.property_grid.setup_by_element(listener)
        self.last_focus = listener

    def remove_focus(self):
        """Set focus to None, and clear property grid"""

        if not self.last_focus:
            return

        self.last_focus.highlight(False)
        self.frame.property_grid.unsetup()
        self.last_focus = None

    def get_active_design_tool(self):
        """Return active edit tool - selected from toolbar"""

        return self.frame.visual_toolbar.get_selected_tool()

    def toggle_double_buffering(self, enabled):
        """Enable or disable double buffering for workspace. 
        
        Needed to fix ogl bug in double buffered containers
        
        """
        self.frame.workspace.SetDoubleBuffered(enabled)

    def report_new(self):
        """Create new report on workspace"""

        self.remove_focus()
        self.frame.workspace.create_new_report()

    def get_predefined_data(self, data_name):
        """Get data element from current report element. 
        
        @return Data element or None if report or data not found
        
        """
        _report = self.frame.workspace.get_report()
        if not _report:
            return None

        _data_list = _report.get_value("lists", "data").get_all()
        for _data in _data_list:
            if _data.get_value("data", "name") == data_name:
                return _data

        return None

    def get_work_dir(self):
        """Return report['basedir'] if set or '.' by default"""

        DEFAULT_DIR = "."

        _report = self.frame.workspace.get_report()
        if not _report:
            return DEFAULT_DIR

        _basedir = _report.get_value("report", "basedir")
        if _basedir is None or _basedir == "":
            return DEFAULT_DIR
        else:
            return _basedir
