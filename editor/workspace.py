"""Place for editing report"""
"""
20-mar-2012 [kacah]   created

"""
import wx
import wx.lib.scrolledpanel as wxscrolled

from elements import report
import environment as env
import utils

class Page(wx.Panel):
    """Page for the report. Include margins and white color."""

    class Margin(wx.Panel):
        """Free space on the page's edges"""

        def __init__(self, parent, size):
            wx.Panel.__init__(self, parent, size=size)
            self.SetBackgroundColour("white")

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.SetBackgroundColour("white")

        self.rep_sizer = wx.BoxSizer(wx.VERTICAL)
        self.report = report.Report(self, self)
        self.report.Expand()
        self.rep_sizer.Add(self.report, 0, wx.VERTICAL)

        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox.Add(self.rep_sizer, 0, wx.HORIZONTAL, 0)

        self.SetSizer(self.hbox)
        self.update_margins()

    def Refresh(self):
        """Setup scrolling for parent, for Workspace"""
        wx.Panel.Refresh(self)
        self.GetParent().SetupScrolling(scrollToTop=False)

    def update_margins(self):
        """Change margins of page from report"""
        self.hbox.Detach(self.rep_sizer)
        self.hbox.Clear(True)
        self.rep_sizer.Detach(self.report)
        self.rep_sizer.Clear(True)

        _addFlag = wx.SizerFlags(0)
        (_top_m, _right_m, _bot_m, _left_m) = self.report.get_margins()

        #add top and bottom free space into VERTICAL BoxSizer
        _margin_top = Page.Margin(self, (-1, utils.dim_to_screen(_top_m)))
        _margin_bottom = Page.Margin(self, (-1, utils.dim_to_screen(_bot_m)))

        self.rep_sizer.Add(_margin_top, 0)
        self.rep_sizer.Add(self.report, 0)
        self.rep_sizer.Add(_margin_bottom, 0)

        #add left and right free space into HORIZONTAL BoxSizer
        _margin_left = Page.Margin(self, (utils.dim_to_screen(_left_m), -1))
        _margin_right = Page.Margin(self, (utils.dim_to_screen(_right_m), -1))

        self.hbox.Add(_margin_left, 0)
        self.hbox.Add(self.rep_sizer, 0)
        self.hbox.Add(_margin_right, 0)

        self.GetParent().SetupScrolling(scrollToTop=False)


class Workspace(wxscrolled.ScrolledPanel):
    """Container for report."""

    def __init__(self, parent):
        wxscrolled.ScrolledPanel.__init__(self, parent, wx.ID_ANY)

        self.SetDoubleBuffered(True)
        self.SetBackgroundColour("grey")

        self.page_sizer = wx.BoxSizer(wx.VERTICAL)
        self.page = None

        #HALIGN CENTER
        _hbox = wx.BoxSizer(wx.HORIZONTAL)
        _hbox.AddStretchSpacer()
        _hbox.Add(self.page_sizer, 0, wx.HORIZONTAL, 0)
        _hbox.AddStretchSpacer()

        self.SetSizer(_hbox)
        self.SetAutoLayout(True)
        self.SetupScrolling()

        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def create_new_report(self):
        """Destroy old and create new Report element"""

        self.page_sizer.Clear(True)

        self.page = Page(self)
        self.page_sizer.Add(self.page, 0, wx.ALL, 25)

    def OnChildFocus(self, evt):
        """Do nothing on child focus to prevent autoscrolling"""
        pass

    TEXTURE_LINE_WIDTH = 2
    SCROLLBARS_COMPENSATION = 30

    def OnPaint(self, event):
        """Paint stripes on this panel"""

        dc = wx.PaintDC(self)
        self.DoPrepareDC(dc)

        pen = wx.Pen(wx.BLACK, self.TEXTURE_LINE_WIDTH)
        dc.SetPen(pen)

        _draw_step = self.TEXTURE_LINE_WIDTH * 2

        (_width, _height) = self.GetVirtualSize()
        for _x in range(0, _width / _draw_step + self.SCROLLBARS_COMPENSATION):
            dc.DrawLine(_x * _draw_step, 0, _x * _draw_step, _height)
