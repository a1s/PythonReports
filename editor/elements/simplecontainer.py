"""Simple container of elements (Header, Footer, Title, Summary, Detail)"""
"""
20-mar-2012 [kacah]   created

"""
import wx

from container import Container
from propertiesgrid import PropertiesListener

class SimpleContainer(Container, PropertiesListener):
    def __init__(self, parent, prop_grid, title, width):
        Container.__init__(self, parent, title, width, wx.SIMPLE_BORDER)
        PropertiesListener.__init__(self, prop_grid)

        self.MakePaneContent(self.GetPane())

        self.GetButton().Bind(wx.EVT_SET_FOCUS, self.OnSelected)

    def MakePaneContent(self, pane):
        """Just make a few controls to put on the collapsible pane"""

        nameLbl = wx.StaticText(pane, -1, "Name:")
        name = wx.TextCtrl(pane, -1, "");

        addrLbl = wx.StaticText(pane, -1, "Address:")
        addr1 = wx.TextCtrl(pane, -1, "");
        addr2 = wx.TextCtrl(pane, -1, "");

        cstLbl = wx.StaticText(pane, -1, "City, State, Zip:")
        city = wx.TextCtrl(pane, -1, "", size=(150, -1));
        state = wx.TextCtrl(pane, -1, "", size=(50, -1));
        zip = wx.TextCtrl(pane, -1, "", size=(70, -1));

        addrSizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        addrSizer.AddGrowableCol(1)
        addrSizer.Add(nameLbl, 0,
                wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        addrSizer.Add(name, 0, wx.EXPAND)
        addrSizer.Add(addrLbl, 0,
                wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        addrSizer.Add(addr1, 0, wx.EXPAND)
        addrSizer.Add((5, 5))
        addrSizer.Add(addr2, 0, wx.EXPAND)

        addrSizer.Add(cstLbl, 0,
                wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)

        cstSizer = wx.BoxSizer(wx.HORIZONTAL)
        cstSizer.Add(city, 1)
        cstSizer.Add(state, 0, wx.LEFT | wx.RIGHT, 5)
        cstSizer.Add(zip)
        addrSizer.Add(cstSizer, 0, wx.EXPAND)

        border = pane.GetSizer()
        border.Add(addrSizer, 1, wx.EXPAND | wx.ALL, 5)
