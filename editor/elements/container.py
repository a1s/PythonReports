"""Expandable element-container"""
"""
20-mar-2012 [kacah]   created

"""
import wx
import wx.lib.agw.pycollapsiblepane as wxpcp
import wx.lib.buttons as wxbtns

class HeaderButton(wxbtns.GenButton):
    """Used for creating containers' header button"""

    HEADER_WIDTH = 25

    def __init__(self, parent, title, width):
        wxbtns.GenButton.__init__(self, parent, wx.ID_ANY, title,
            size=(width, self.HEADER_WIDTH))
        self.SetForegroundColour("white")
        self.SetBackgroundColour("grey")

    def DoGetBestSize(self):
        """Header must not be auto resizable"""
        return self.GetSize()


class Container(wxpcp.PyCollapsiblePane):
    """Contains drawable elements"""

    def __init__(self, parent, title, width, border=wx.NO_BORDER):
        wxpcp.PyCollapsiblePane.__init__(self, parent, style=border,
            agwStyle=wx.CP_NO_TLW_RESIZE | wx.CP_LINE_ABOVE)

        _head_btn = HeaderButton(self, title, width)
        self.SetButton(_head_btn)
        self.Unbind(wx.EVT_BUTTON, self._pButton)
        _head_btn.Bind(wx.EVT_LEFT_DCLICK, self.OnButton)

        self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.OnPaneChanged, self)

        _sizer = wx.BoxSizer(wx.VERTICAL)
        self.GetPane().SetSizer(_sizer)

    def OnPaneChanged(self, evt=None):
        """Update layout and try to update parents"""

        #update self size to fit all changed children
        self.OnStateChange(self.GetBestSize())

        #do this if container is inside Scrollpanel
        try:
            self.GetParent().SetupScrolling()
        except:
            pass
        #do this if container is inside another container
        try:
            self.GetParent().GetParent().OnPaneChanged()
        except:
            pass

    def insert_element(self, element, position):
        """Insert new element at position"""

        _sizer = self.GetPane().GetSizer()
        _sizer.Insert(position, element, 0, wx.VERTICAL, 0)
        self.OnPaneChanged()

    def add_element(self, element):
        """Add new element at the end"""

        _sizer = self.GetPane().GetSizer()
        _sizer.Add(element, 0, wx.VERTICAL, 0)
        self.OnPaneChanged()
