"""Expandable element-container"""
"""
30-mar-2012 [kacah]    Added detach and remove methods
20-mar-2012 [kacah]    created

"""
import wx
import wx.lib.agw.pycollapsiblepane as wxpcp
import wx.lib.buttons as wxbtns

class HeaderButton(wxbtns.GenButton):
    """Used for creating containers' header button"""

    HEADER_HEIGHT = 25
    NORMAL_FG_COLOR = "black"
    NORMAL_BG_COLOR = wx.Colour(195, 195, 195)

    def __init__(self, parent, title, width):
        wxbtns.GenButton.__init__(self, parent, wx.ID_ANY, title,
            size=(width, self.HEADER_HEIGHT))

        self.width = width

        self.SetForegroundColour(self.NORMAL_FG_COLOR)
        self.SetBackgroundColour(self.NORMAL_BG_COLOR)

    def set_width(self, width):
        """Set width of element"""

        self.width = width
        self.SetSize(self.DoGetBestSize())

    def highlight(self, need_hl):
        """Highlight this button"""

        if need_hl:
            self.SetForegroundColour("white")
            self.SetBackgroundColour(wx.Colour(0, 0, 0))
        else:
            self.SetForegroundColour(self.NORMAL_FG_COLOR)
            self.SetBackgroundColour(self.NORMAL_BG_COLOR)
        self.Refresh()

    def DoGetBestSize(self):
        """Header must not be auto resizable"""
        return (self.width, self.HEADER_HEIGHT)


class Container(wxpcp.PyCollapsiblePane):
    """Contains drawable elements"""

    def __init__(self, parent, title, width, border=wx.NO_BORDER):
        wxpcp.PyCollapsiblePane.__init__(self, parent, style=border,
            agwStyle=wx.CP_NO_TLW_RESIZE)

        _head_btn = HeaderButton(self, title, width)
        self.SetButton(_head_btn)
        self.Unbind(wx.EVT_BUTTON, self._pButton)
        _head_btn.Bind(wx.EVT_LEFT_DCLICK, self.OnButton)

        self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.OnPaneChanged, self)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.GetPane().SetSizer(self.sizer)

    def OnPaneChanged(self, evt=None):
        """Update layout and try to update parents"""

        #update self size to fit all changed children
        self.OnStateChange(self.GetBestSize())

        #do this if container is inside another container
        #first parent is Containers.Pane, second is Container
        try:
            self.GetParent().GetParent().OnPaneChanged()
        except:
            pass

        #refresh parent
        self.GetParent().Refresh()

    def highlight(self, need_hl):
        """Highlight this container"""
        self.GetButton().highlight(need_hl)

    def set_width(self, width):
        """Set width of container element"""

        self.GetButton().set_width(width)
        self.OnPaneChanged()

    def get_width(self):
        """Get width of container element"""

        return self.GetButton().GetSize().GetWidth()

    def set_visible(self, visible):
        """Set element visible or not"""

        self.Show(visible)

    def set_title(self, title):
        """Set title of this container"""

        self.SetLabel(title)

    def insert_element(self, element, position):
        """Insert new element at position"""

        self.sizer.Insert(position, element, 0, wx.VERTICAL)
        self.OnPaneChanged()

    def add_element(self, element):
        """Add new element at the end"""

        self.sizer.Add(element, 0, wx.VERTICAL)
        self.OnPaneChanged()

    def detach_element(self, element):
        """Detach element from container. Doesn't destroy it."""

        self.sizer.Detach(element)
        self.OnPaneChanged()

    def remove_element(self, element):
        """Detach element from container and destroy it."""

        self.sizer.Remove(element)
        self.OnPaneChanged()

    def detach_all(self):
        """Detach all elements from container (not destroying them)"""

        self.sizer.Clear(False)
        self.OnPaneChanged()

    def remove_all(self):
        """Destroy all elements in container"""

        self.sizer.Clear(True)
        self.OnPaneChanged()
