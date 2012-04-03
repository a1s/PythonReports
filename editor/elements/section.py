"""Simple container of elements (Header, Footer, Title, Summary, Detail)"""
"""
03-apr-2012 [kacah]    Added DesignPlace
20-mar-2012 [kacah]    created

"""
import PythonReports.template as te
import wx
import wx.lib.ogl as wxogl
import wx.lib.resizewidget as wxrw

from container import Container
from elements.element import Element

MIN_SIZE = 10

class DesignPlace(wxogl.ShapeCanvas):
    """Place for painting visual elements"""

    def __init__(self, parent, width):
        wxogl.ShapeCanvas.__init__(self, parent, size=(width, MIN_SIZE))

        self.SetMinSize((width, MIN_SIZE))
        self.SetMaxSize((width, -1))

        self.diagram = wxogl.Diagram()
        self.SetDiagram(self.diagram)

    def set_width(self, width):
        """Set min, max and actual width of design place"""

        self.SetSize((width, self.GetSize().GetHeight()))
        self.SetMinSize((width, MIN_SIZE))
        self.SetMaxSize((width, -1))


UNRESTRICTED_VALIDATORS = [te.Eject, te.Style, te.Subreport]

class Section(Container, Element):
    """Container for visual elements like fields, images, barcodes..."""

    def __init__(self, parent, prop_grid, title, width):
        Container.__init__(self, parent, title, width)
        Element.__init__(self, prop_grid,
            unrestricted_val=UNRESTRICTED_VALIDATORS)

        self.GetButton().Bind(wx.EVT_SET_FOCUS, self.OnSelected)

        self.resizer = wxrw.ResizeWidget(self.GetPane())
        self.design_place = DesignPlace(self.resizer, width)
        self.add_element(self.resizer)

        self.Bind(wxrw.EVT_RW_LAYOUT_NEEDED, self.OnPaneChanged)

    def set_width(self, width):
        """Set width of container element"""

        self.design_place.set_width(width)
        #AdjustToChild doesn't work cause of an error in wx.lib.resizewidget.py
        self.resizer.AdjustToSize(self.design_place.GetSize())
        Container.set_width(self, width)
