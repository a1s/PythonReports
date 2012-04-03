"""Place for editing report"""
"""
20-mar-2012 [kacah]   created

"""
import wx
import wx.lib.scrolledpanel as wxscrolled

from elements import report

class Workspace(wxscrolled.ScrolledPanel):
    """Container for report."""

    def __init__(self, parent, prop_grid):
        wxscrolled.ScrolledPanel.__init__(self, parent, wx.ID_ANY)

        self.prop_grid = prop_grid

        _vbox = wx.BoxSizer(wx.VERTICAL)
        self.report = report.Report(self, prop_grid)
        self.report.Expand()
        _vbox.Add(self.report, 0, wx.VERTICAL | wx.TOP, 25)

        #HALIGN CENTER
        _hbox = wx.BoxSizer(wx.HORIZONTAL)
        _hbox.AddStretchSpacer()
        _hbox.Add(_vbox, 0, wx.HORIZONTAL, 0)
        _hbox.AddStretchSpacer()

        self.SetSizer(_hbox)
        self.SetAutoLayout(True)
        self.SetupScrolling()
