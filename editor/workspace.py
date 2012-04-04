"""Place for editing report"""
"""
20-mar-2012 [kacah]   created

"""
import wx
import wx.lib.scrolledpanel as wxscrolled

from elements import report
import environment as env

class Workspace(wxscrolled.ScrolledPanel):
    """Container for report."""

    def __init__(self, parent):
        wxscrolled.ScrolledPanel.__init__(self, parent, wx.ID_ANY)
        self.SetDoubleBuffered(True)

        self.rep_sizer = wx.BoxSizer(wx.VERTICAL)
        self.report = None

        #HALIGN CENTER
        _hbox = wx.BoxSizer(wx.HORIZONTAL)
        _hbox.AddStretchSpacer()
        _hbox.Add(self.rep_sizer, 0, wx.HORIZONTAL, 0)
        _hbox.AddStretchSpacer()

        self.SetSizer(_hbox)
        self.SetAutoLayout(True)
        self.SetupScrolling()

    def create_new_report(self):
        """Destroy old and create new Report element"""

        self.rep_sizer.Clear(True)

        self.report = report.Report(self)
        self.report.Expand()
        self.rep_sizer.Add(self.report, 0, wx.VERTICAL | wx.TOP, 25)

    def OnChildFocus(self, evt):
        """Do nothing on child focus to prevent autoscrolling"""
        pass
