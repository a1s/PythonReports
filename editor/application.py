"""Contain global application objects and data. Link objects."""
"""
04-apr-2012 [kacah]    created

"""
import os

import wx

from mainform import EditorForm
import templateloader, templatesaver
import utils

class EditorApplication(wx.App):
    """Main class, environment of editor"""

    def __init__(self):
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

    def focus_get(self):
        """Get focused element"""

        return self.last_focus

    def focus_set(self, listener, call_tree_update=True):
        """Unfocus last element, focus new, update properties in prop grid"""

        #do not add check 'listener == self.last_focus'
        #this function can also update focus, tree and property grid
        self.focus_remove(False)
        listener.highlight(True)
        self.frame.property_grid.setup_by_element(listener)
        self.last_focus = listener
        if call_tree_update:
            self.elemtree_update_report()

    def focus_remove(self, call_tree_update=True):
        """Set focus to None, and clear property grid"""

        if not self.last_focus:
            return

        self.last_focus.highlight(False)
        self.frame.property_grid.unsetup()
        self.last_focus = None

        if call_tree_update:
            self.elemtree_update_report()

    def focus_move_up(self):
        """Change element z index up if available"""

        if not self.last_focus:
            return

        if hasattr(self.last_focus, "move_up"):
            self.last_focus.move_up()
            self.elemtree_update_report()

    def focus_move_down(self):
        """Change element z index down if available"""

        if not self.last_focus:
            return

        if hasattr(self.last_focus, "move_down"):
            self.last_focus.move_down()
            self.elemtree_update_report()

    def focus_delete(self):
        """Delete focused element if it has 'delete' method"""

        if not self.last_focus:
            return

        if hasattr(self.last_focus, "delete"):
            _to_delete = self.last_focus
            self.focus_remove()
            _to_delete.delete()
            self.elemtree_update_report()

    def report_new(self):
        """Create new report on workspace"""

        self.focus_remove()
        self.frame.workspace.create_new_report()
        self.focus_set(self.frame.workspace.get_report())

    def report_open(self):
        """Show dialog and open template in workspace"""

        _dlg = wx.FileDialog(self.frame, "Choose a template file", os.getcwd(),
            "", "*.*", wx.OPEN)
        if _dlg.ShowModal() == wx.ID_OK:
            _file_name = _dlg.GetPath()
            _dlg.Destroy()
        else:
            _dlg.Destroy()
            return

        try:
            _template = templateloader.load_template_file(_file_name)
        except Exception, _ex:
            #TODO add user friendly error reporting here
            print "Invalid template file"
            return

        self.report_new()
        _report = self.frame.workspace.get_report()
        templateloader.load_template(_template, _report)
        self.focus_set(_report)

    def report_save(self):
        """Show dialog and save template from workspace"""

        _report = self.frame.workspace.get_report()
        if not _report:
            return

        _dlg = wx.FileDialog(self.frame, "Choose a template file", os.getcwd(),
            "", "*.*", wx.SAVE)
        if _dlg.ShowModal() == wx.ID_OK:
            _file_name = _dlg.GetPath()
            _dlg.Destroy()
        else:
            _dlg.Destroy()
            return

        try:
            templatesaver.save_template_file(_report, _file_name)
        except Exception, _ex:
            #TODO add user friendly error reporting here
            print "Error saving template file", _ex

    def app_close(self):
        """Close this application"""

        self.frame.OnClose()

    def zoom_get(self):
        """Get zoom of workspace"""

        return self.frame.workspace.zoom

    def zoom_in(self):
        """Zoom in workspace"""

        self.frame.workspace.zoom_in()

    def zoom_out(self):
        """Zoom out workspace"""

        self.frame.workspace.zoom_out()

    def elemtree_update_report(self):
        """Update elements tree from tree root - report"""

        self.frame.elements_tree.build_report_items(
            self.frame.workspace.get_report())

    def toggle_double_buffering(self, enabled):
        """Enable or disable double buffering for workspace. 
        
        Needed to fix ogl bug in double buffered containers
        
        """
        self.frame.workspace.SetDoubleBuffered(enabled)

    def design_tool_get(self):
        """Return active edit tool - selected from toolbar"""

        return self.frame.visual_toolbar.get_selected_tool()

    def design_tool_set(self, design_tool):
        """Set active edit tool on toolbar"""

        self.frame.visual_toolbar.set_selected_tool(design_tool)

    def get_predefined_data(self, data_name):
        """Get data element from current report element. 
        
        @return: Data element or None if report or data not found
        
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
