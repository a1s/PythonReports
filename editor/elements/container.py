"""Expandable element-container"""
"""
30-mar-2012 [kacah]    Added detach and remove methods
20-mar-2012 [kacah]    created

"""
import wx
import wx.lib.agw.pycollapsiblepane as wxpcp
import wx.lib.platebtn as wxpltbns


class HeaderButton(wxpltbns.PlateButton):
    """Used for creating containers' header button"""

    HEADER_HEIGHT = 25
    PRESS_COLOR = wx.Colour(0, 0, 0)

    def __init__(self, parent, title, width, bk_color=None):
        self.width = width
        _style = wxpltbns.PB_STYLE_SQUARE | wxpltbns.PB_STYLE_TOGGLE
        if not bk_color:
            _style = _style | wxpltbns.PB_STYLE_NOBG

        wxpltbns.PlateButton.__init__(self, parent, wx.ID_ANY, title,
            size=(width, self.HEADER_HEIGHT), style=_style)

        if bk_color:
            self.SetBackgroundColour(bk_color)

        self.SetPressColor(self.PRESS_COLOR)

    def __PostEvent(self):
        """Post a button event to parent of this control"""

        _etype = wx.wxEVT_COMMAND_BUTTON_CLICKED
        _bevt = wx.CommandEvent(_etype, self.GetId())
        _bevt.SetEventObject(self)
        _bevt.SetString(self.GetLabel())
        self.GetEventHandler().ProcessEvent(_bevt)

    def set_width(self, width):
        """Set width of element"""

        self.width = width
        self.SetSize(self.DoGetBestSize())

    def set_title(self, title):
        """Set title of this button"""

        self.SetLabel(title)

    def get_title(self):
        """Get title of this button"""

        return self.GetLabel()

    def set_visible(self, visible):
        """Set element visible or not"""

        self.Show(visible)

    def OnFocus(self, evt):
        """Don't highlight on focus"""
        pass

    def OnLeftDown(self, evt):
        """Change state to pressed"""

        self.SetState(wxpltbns.PLATE_PRESSED)

    def OnLeftUp(self, evt):
        """Just post button event"""

        self.__PostEvent()

    def highlight(self, need_hl):
        """Highlight this button. Mark it like pressed"""

        self._pressed = need_hl
        if need_hl:
            self.SetState(wxpltbns.PLATE_PRESSED)
        else:
            self.SetState(wxpltbns.PLATE_NORMAL)

    def DoGetBestSize(self):
        """Header must not be auto resizable"""
        return (self.width, self.HEADER_HEIGHT)


class Container(wxpcp.PyCollapsiblePane):
    """Contains drawable elements"""

    HEADER_COLOR = wx.Colour(220, 220, 220)

    def __init__(self, parent, title, width, border=wx.NO_BORDER):
        wxpcp.PyCollapsiblePane.__init__(self, parent, style=border,
            agwStyle=wx.CP_NO_TLW_RESIZE)

        _head_btn = HeaderButton(self, title, width, self.HEADER_COLOR)
        self.SetButton(_head_btn)
        self.Unbind(wx.EVT_BUTTON, self._pButton)
        _head_btn.Bind(wx.EVT_LEFT_DCLICK, self.OnButton)

        self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.OnExpandedCollapsed, self)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.GetPane().SetSizer(self.sizer)

    def OnExpandedCollapsed(self, evt):
        self.OnPaneChanged()

    def OnPaneChanged(self):
        """Update layout and try to update parents"""

        #update self size to fit all changed children
        self.OnStateChange(self.GetBestSize())

        #do this if container is inside another container
        #first parent is Containers.Pane, second is Container
        try:
            self.GetParent().GetParent().OnPaneChanged()
        except AttributeError:
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

    def get_title(self):
        """Get title of this container"""

        return self.GetLabel()

    def insert_element(self, element, position, left_gap=0):
        """Insert new element at position"""

        self.sizer.Insert(position, element, 0, wx.VERTICAL | wx.LEFT, left_gap)
        self.OnPaneChanged()

    def add_element(self, element, left_gap=0):
        """Add new element at the end"""

        self.sizer.Add(element, 0, wx.VERTICAL | wx.LEFT, left_gap)
        self.OnPaneChanged()

    def detach_element(self, element):
        """Detach element from container. Doesn't destroy it."""

        self.sizer.Detach(element)
        self.OnPaneChanged()

    def remove_element(self, element):
        """Detach element from container and destroy it."""

        self.sizer.Remove(element)
        self.OnPaneChanged()

    def get_all(self):
        """Get all elements managed by container"""

        return self.sizer.GetChildren()

    def detach_all(self):
        """Detach all elements from container (not destroying them)"""

        self.sizer.Clear(False)
        self.OnPaneChanged()

    def remove_all(self):
        """Destroy all elements in container"""

        self.sizer.Clear(True)
        self.OnPaneChanged()
