"""Main element, Root of template"""
"""
20-mar-2012 [kacah]   created

"""
import PythonReports.template as templelem
import wx

from container import Container
from elements.element import Element
from simplecontainer import SimpleContainer

DEFAULT_WIDTH = 600
#sequence is important
SECTION_NAMES = ["Title", "Header", "Detail", "Footer", "Summary"]
MAIN_VALIDATOR = templelem.Report
ZERO_OR_ONE_VALIDATORS = [templelem.Columns]
ONE_VALIDATORS = [templelem.Layout]
UNRESTRICTED_VALIDATORS = [templelem.Group, templelem.Style]

class Report(Container, Element):
    """Main, Report element, Root of template"""

    def __init__(self, parent, prop_grid):
        Container.__init__(self, parent, "Report", DEFAULT_WIDTH)
        Element.__init__(self, prop_grid,
            MAIN_VALIDATOR, ZERO_OR_ONE_VALIDATORS,
            ONE_VALIDATORS, UNRESTRICTED_VALIDATORS)

        self.sections = self.create_sections(SECTION_NAMES)
        self.columns = None
        self.groups = []

        self.GetButton().Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)

    def create_sections(self, sections_list):
        """Create many sections to report by given list
        
        @return Dictionary of sections created, linked with their names
        
        """
        _sections = {}
        for _section in sections_list:
            _sections[_section] = SimpleContainer(self.GetPane(), self.prop_grid,
                _section, DEFAULT_WIDTH)
            self.add_element(_sections[_section])
        return _sections
