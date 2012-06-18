"""Simple container of elements (Header, Footer, Title, Summary, Detail)"""
"""
11-apr-2012 [kacah]    Design place moved to design.py, added Subreport
03-apr-2012 [kacah]    Added DesignPlace
20-mar-2012 [kacah]    created

"""
from PythonReports import datatypes
import PythonReports.template as te
import wx
import wx.lib.resizewidget as wxrw

from container import Container, HeaderButton
from design import DesignPlace
from element import Element
from .. import utils


SUBREPORT_MAIN = te.Subreport
SUBREPORT_UNRESTRICTED = [te.Arg]

class Subreport(HeaderButton, Element):
    """PythonReports subreport element"""

    def __init__(self, parent, width, subreport_id, section):
        HeaderButton.__init__(self, parent, "Subreport", width)
        Element.__init__(self, SUBREPORT_MAIN,
            unrestricted_val=SUBREPORT_UNRESTRICTED)

        self.id = subreport_id
        self.section = section

        self.Bind(wx.EVT_BUTTON, self.OnFocus)

    def OnFocus(self, evt=None):
        wx.GetApp().focus_set(self)

    def destroy(self):
        """Destroy self"""
        self.Destroy()

    def set_title(self, title):
        """Set title of element"""
        self.SetLabel(title)

    def get_sequence(self):
        """Get seq value of Subreport"""
        return self.get_value("subreport", "seq")

    def update_name(self):
        """Update subreport name from properties"""

        _name = self.get_value("subreport", "template")
        _name = "Subreport '%s'" % _name
        self.set_title(_name)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if category == "subreport":
            self.update_name()
            self.section.synchronize_subreport(self)

SectionBox = datatypes.Validator(tag="box",
    attributes={
        "height": (datatypes.Dimension, -1),
    }, doc="Only height attribute is needed for sections"
)
UNRESTRICTED_VALIDATORS = [te.Eject, te.Style, te.Subreport]
ONE_VALIDATORS = [SectionBox]

class SectionResizer(wxrw.ResizeWidget):
    """Visual resizer for section"""

    def __init__(self, parent, section):
        wxrw.ResizeWidget.__init__(self, parent)
        self.section = section

    def OnLeftUp(self, evt):
        wxrw.ResizeWidget.OnLeftUp(self, evt)

        self.section.synchronize_height()
        wx.GetApp().focus_set(self.section)


class Section(Container, Element):
    """Container for visual elements like fields, images, barcodes..."""

    CHILD_LEFT_OFFSET = 3

    def __init__(self, parent, title, width):
        Container.__init__(self, parent, title, width)
        Element.__init__(self, one_val=ONE_VALIDATORS,
            unrestricted_val=UNRESTRICTED_VALIDATORS)

        self.GetButton().Bind(wx.EVT_BUTTON, self.OnFocus)

        self.design_resizer = SectionResizer(self.GetPane(), self)
        self.design_place = DesignPlace(self.GetPane(), width, self)
        self.design_resizer.SetManagedChild(self.design_place)

        self.add_element(self.design_resizer, self.CHILD_LEFT_OFFSET)

        self.subreports = []

        self.Bind(wxrw.EVT_RW_LAYOUT_NEEDED, self.OnExpandedCollapsed)
        self.synchronize_height()

    def OnFocus(self, evt=None):
        wx.GetApp().focus_set(self)

    def set_height(self, height):
        """Set height of container element"""

        self.design_place.set_height(height)
        self.design_resizer.AdjustToSize(self.design_place.GetSize())

        self.OnPaneChanged()

    def adjust_to_design_place(self):
        """Adjust section height to lowest element in design place"""

        self.set_height(self.design_place.get_lowest_point())

    def get_height(self):
        """Get height of section"""

        return self.design_place.GetSize()[1]

    def set_width(self, width):
        """Set width of container element"""

        self.GetButton().set_width(width)
        self.design_place.set_width(width)
        #AdjustToChild doesn't work cause of an error in wx.lib.resizewidget.py
        self.design_resizer.AdjustToSize(self.design_place.GetSize())

        for _subreport in self.subreports:
            _subreport.set_width(width)

        self.OnPaneChanged()

    def _create_subreport(self, id):
        """Create subreport with given id"""

        return Subreport(self.GetPane(), self.get_width(), id, self)

    def _update_subreport(self, subreport):
        """Update one group element"""

        subreport.update_name()

    def _insert_elements(self):
        """Insert subreports and design_place into section"""

        LEFT_OFFSET = 3

        self.subreports.sort(key=lambda sub: sub.get_sequence())

        added_design = False

        for _sub in self.subreports:
            #check if need to add design_resizer in the middle of subreports
            if (not added_design) and (_sub.get_sequence() > 0):
                self.add_element(self.design_resizer, self.CHILD_LEFT_OFFSET)
                added_design = True

            self.add_element(_sub, self.CHILD_LEFT_OFFSET)

        if not added_design:
            self.add_element(self.design_resizer, self.CHILD_LEFT_OFFSET)

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
        _sub_value.synchronize_attributes("subreport",
            sub.get_category("subreport"))

    def force_data_update(self):
        """Update all elements that are linked to report data"""
        self.design_place.force_data_update()

    def update_height(self):
        """Update section height from properties"""

        _height = self.get_value("box", "height")

        if _height < 0:
            self.adjust_to_design_place()
        else:
            self.set_height(utils.dim_to_screen(_height))

    def synchronize_height(self):
        """Put current section height to properties"""

        self.set_value("box", "height", utils.screen_to_dim(self.get_height()))

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if (category == "lists") and (attribute == "subreport"):
            self.update_subreports()

        if attribute == "height":
            self.update_height()
