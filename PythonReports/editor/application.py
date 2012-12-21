#! /usr/bin/env python
"""PythonReports Template Editor application"""

from cStringIO import StringIO
import os
import sys

import wx

from PythonReports import wxPrint, pdf
from PythonReports.builder import Builder

from mainform import EditorForm
import templateloader, templatesaver
import utils

NEW_REPORT_TEMPLATE = """<report>
 <font name="body" typeface="Arial" size="8" />
 <layout pagesize="A4" leftmargin="2.5cm" rightmargin="1.5cm"
  topmargin="1.5cm" bottommargin="1.5cm">
  <style font="body" color="0" bgcolor="white" />
  <header><box height="20" /></header>
  <footer><box height="20" /></footer>
  <title><box height="20" /></title>
  <summary><box height="20" /></summary>
  <detail><box height="20" /></detail>
 </layout>
</report>
"""

class EditorApplication(wx.App):
    """Main class, environment of editor"""

    # Wildcards for File Open and Save As dialogs
    FILE_WILDCARDS = "Template files (*.prt)|*.prt|All files|*.*"

    last_directory = None
    filename = None

    def __init__(self, *args, **kwargs):
        wx.App.__init__(self, *args, **kwargs)

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

        if self.frame.workspace.get_report():
            _dlg = wx.MessageDialog(self.frame,
                "You will loose your current template."
                " Do you want to create new one?",
                "Confirm new report", wx.OK | wx.CANCEL | wx.ICON_WARNING)

            _dlg_result = _dlg.ShowModal()
            _dlg.Destroy()

            if _dlg_result != wx.ID_OK:
                return

        self.filename = None
        self.focus_remove()
        self.frame.workspace.create_new_report()
        _report = self.frame.workspace.get_report()
        _template = templateloader.load_template_file(
            StringIO(NEW_REPORT_TEMPLATE))
        templateloader.load_template(_template, _report)
        self.focus_set(_report)

    def report_open(self, filename=None):
        """Show dialog and open template in workspace"""

        if not filename:
            _dlg = wx.FileDialog(self.frame, "Choose a template file",
                self.last_directory or os.getcwd(), "",
                self.FILE_WILDCARDS, wx.OPEN)
            if _dlg.ShowModal() == wx.ID_OK:
                filename = _dlg.GetPath()
                _dlg.Destroy()
            else:
                _dlg.Destroy()
                return
        self.last_directory = os.path.abspath(os.path.dirname(filename))
        try:
            _template = templateloader.load_template_file(filename)
        except StandardError, _ex:
            #TODO: add user friendly error reporting here
            print "Invalid template file"
            raise

        self.focus_remove()
        self.frame.workspace.create_new_report()
        _report = self.frame.workspace.get_report()
        templateloader.load_template(_template, _report)
        self.focus_set(_report)
        self.filename = filename

    def report_save_file(self, filename=None):
        """Save template from the workspace

        If output file name is omitted or empty,
        open "Save As..." file selection dialog.

        """

        _report = self.frame.workspace.get_report()
        if not _report:
            return

        if not filename:
            filename = self.get_output_file_name("Choose a template file",
                self.FILE_WILDCARDS, self.filename)
            if not filename:
                return
        try:
            templatesaver.save_template_file(_report, filename)
            self.filename = filename
        except StandardError, _ex:
            self.filename = None
            #TODO: add user friendly error reporting here
            print "Error saving template file", _ex
            raise
        self.last_directory = os.path.abspath(os.path.dirname(filename))

    def report_save(self):
        """Save template from workspace"""
        self.report_save_file(self.filename)

    def report_build(self):
        """Build and return printout for open template"""
        _data = self.get_report_data()
        _report = self.frame.workspace.get_report()
        if (_data is None) or not _report:
            return None
        _template = templatesaver.create_xml_template(_report)
        _template.validate()
        return Builder(_template).run(_data)

    def report_preview(self):
        """Build report printout and display it in a preview frame"""
        _printout = self.report_build()
        if not _printout:
            return
        _printout.validate()
        _preview = wxPrint.Preview(_printout)
        if self.filename:
            _title = "%s preview" % os.path.basename(self.filename)
        else:
            _title = "Report preview"
        if self.frame.IsMaximized():
            _size = wx.Size(800, 600)
        else:
            _size = self.frame.GetSize()
        _frame = wx.PreviewFrame(_preview, self.frame, _title, size=_size)
        _frame.Initialize()
        _frame.Show(True)

    def report_write_printout(self):
        """Build report printout and save it in a disk file"""
        _filename = self.get_output_file_name("Save As",
            "Report Printout files (*.prp)|*.prp|All files|*.*",
            self.filename, "prp")
        if _filename:
            _printout = self.report_build()
            if _printout:
                _printout.validate()
                _printout.write(_filename)

    def report_write_pdf(self):
        """Build report printout and write PDF output"""
        _filename = self.get_output_file_name("Save As",
            "PDF files|*.pdf|All files|*.*", self.filename, "pdf")
        if _filename:
            _printout = self.report_build()
            if _printout:
                _printout.validate()
                pdf.write(_printout, _filename)

    def get_output_file_name(self, title, wildcard, default, setext=None):
        """Open "Save As" file dialog, return file path or C{None}

        @param title: title string for the file dialog.

        @param wildcard: file selection wildcards.

        @param default: default file name.

        @param setext: output file extension.

            If passed, extension of the default file name (if any)
            is changed to this string.

        @return: file name selected in the file dialog.

            If the dialog is cancelled, return C{None}.

        """
        if default:
            _filename = default
            if setext:
                _filename = os.path.splitext(_filename)[0] + "." + setext
        else:
            _filename = ""
        _dlg = wx.FileDialog(self.frame, title,
            self.last_directory or os.getcwd(), _filename, wildcard, wx.SAVE)
        if _dlg.ShowModal() == wx.ID_OK:
            _rv = _dlg.GetPath()
        else:
            _rv = None
        _dlg.Destroy()
        return _rv

    def get_report_data(self):
        """Return data sequence for report preview or output

        If the report cannot be run, return C{None}

        """
        if not self.frame.workspace.get_report():
            _dlg = wx.MessageDialog(self.frame, "No template loaded",
                "Error", wx.ICON_EXCLAMATION | wx.OK)
            _dlg.ShowModal()
            _dlg.Destroy()
            return
        # get the data
        _vars = self.frame.shell.interp.locals
        _message = None
        try:
            _data = _vars["data"]
        except KeyError:
            _message = "Report data sequence is not defined.\n" \
                "Please set \"data\" variable in the shell.\n\n" \
                "Press <Ok> to run the report with empty sequence\n" \
                "or <Cancel> to return to designer window."
        else:
            if not _data:
                _message = "Report data sequence is empty.\n\n" \
                    "Run the report anyway?"
        if _message:
            _dlg = wx.MessageDialog(self.frame, _message,
                "Missing Report data",
                wx.ICON_EXCLAMATION | wx.OK | wx.CANCEL)
            _rv = _dlg.ShowModal()
            _dlg.Destroy()
            if _rv == wx.ID_OK:
                _data = ()
            else:
                return None
        return _data

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

    def get_main_frame(self):
        """Return main frame of editor"""

        return self.frame

# vim: set et sts=4 sw=4 :
