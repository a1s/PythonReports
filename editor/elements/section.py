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
from elements import design
from elements.element import Element
import environment as env
import utils

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

    def __init__(self, parent, title, width):
        Container.__init__(self, parent, title, width)
        Element.__init__(self, unrestricted_val=UNRESTRICTED_VALIDATORS)

        self.GetButton().Bind(wx.EVT_SET_FOCUS, self.OnFocus)

        self.design_resizer = wxrw.ResizeWidget(self.GetPane())
        self.design_place = DesignPlace(self.design_resizer, width)
        self.add_element(self.design_resizer)

        self.subreports = []

        self.Bind(wxrw.EVT_RW_LAYOUT_NEEDED, self.OnPaneChanged)

    def OnFocus(self, evt=None):
        env.OnPropertyListener(self)

    def set_width(self, width):
        """Set width of container element"""

        self.GetButton().set_width(width)
        self.design_place.set_width(width)
        #AdjustToChild doesn't work cause of an error in wx.lib.resizewidget.py
        self.design_resizer.AdjustToSize(self.design_place.GetSize())
        self.OnPaneChanged()

    def add_element(self, element):
        """Override from Container, expand elements, don't need funny sizes"""

        self.sizer.Add(element, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 3)
        self.OnPaneChanged()

    def _create_subreport(self, id):
        """Create subreport with given id"""

        return design.Subreport(self.GetPane(), self.get_width(), id, self)

    def _update_subreport(self, subreport):
        """Update one group element"""

        subreport.update_name()

    def _insert_elements(self):
        """Insert subreports and design_place into section"""

        self.subreports.sort(key=lambda sub: sub.get_sequence())

        added_design = False

        for _sub in self.subreports:
            #check if need to add design_resizer in the middle of subreports
            if (not added_design) and (_sub.get_sequence() > 0):
                self.add_element(self.design_resizer)
                added_design = True

            self.add_element(_sub)

        if not added_design:
            self.add_element(self.design_resizer)

    def update_subreports(self):
        """Update all groups of report"""

        self.detach_all()

        _new_sub = self.synchronize_list_category("subreport", self.subreports,
            self._create_subreport, self._update_subreport)
        utils.destroy_difference(self.subreports, _new_sub)
        self.subreports = _new_sub

        self._insert_elements()

    def synchronize_subreport(self, sub):
        """Get data from subreport to self"""

        _sub_value = self.get_value("lists", "subreport").get_by_id(sub.id)
        _sub_value.synchronize_attributes(
            "subreport", sub.get_category("subreport"))

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if (category == "lists") and (attribute == "subreport"):
            self.update_subreports()
