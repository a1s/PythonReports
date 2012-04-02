"""Classes for groups and columns"""
"""
30-mar-2012 [kacah]   created

"""

import PythonReports.template as te
import wx

from elements.element import Element
from section import Section

PAIR_TITLE_SUMMARY = 0
PAIR_HEADER_FOOTER = 1
PAIR_TITLES = [("title", "summary"), ("header", "footer")]

class SectionPair(object):
    """Pair of header/footer of title/summary elements"""

    def __init__(self, parent, prop_grid, width, p_id, prefix=""):
        """Create two section elements
        
        @param p_id: 0 - title, summary | 1 - header, footer
        @param prefix: string, prefix of titles
        
        """
        _titles = self.build_titles(prefix, p_id)
        self.first = Section(parent, prop_grid, _titles[0], width)
        self.second = Section(parent, prop_grid, _titles[1], width)

    def build_titles(self, prefix, p_id):
        """Build titles of pair by prefix and pair name id"""

        return (prefix + PAIR_TITLES[p_id][0], prefix + PAIR_TITLES[p_id][1])

    def set_visible(self, visible):
        """Set both pair elements visible or not"""
        self.first.set_visible(visible)
        self.second.set_visible(visible)

    def set_width(self, width):
        """Set width of both pair elements"""
        self.first.set_width(width)
        self.second.set_width(width)

    def get_first(self):
        """Get first section of pair"""
        return self.first

    def get_second(self):
        """Get second element of pair"""
        return self.second

UNRESTRICTED_STYLE = [te.Style]
MAIN_COLUMNS = te.Columns

class Columns(SectionPair, Element):
    """PythonReports Columns element"""

    def __init__(self, parent, prop_grid, width, report):
        SectionPair.__init__(self, parent, prop_grid, width, PAIR_HEADER_FOOTER,
            "Columns ")
        Element.__init__(self, prop_grid, main_val=MAIN_COLUMNS,
            unrestricted_val=UNRESTRICTED_STYLE)

        self.report = report

        self.first.GetButton().Bind(wx.EVT_SET_FOCUS, self.OnSelected)
        self.second.GetButton().Bind(wx.EVT_SET_FOCUS, self.OnSelected)

    def count_width(self, width, number, gap):
        """Count columns width by columns number and gap"""

        return width / number - (number - 1) * gap

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if category == "columns":
            self.report.synchronize_columns()

MAIN_GROUP = te.Group

class Group(SectionPair, Element):
    """PythonReports Group element"""

    def __init__(self, parent, prop_grid, width, group_id, report):
        SectionPair.__init__(self, parent, prop_grid, width, PAIR_TITLE_SUMMARY,
            "Group ")
        Element.__init__(self, prop_grid, main_val=MAIN_GROUP,
            unrestricted_val=UNRESTRICTED_STYLE)

        self.report = report

        self.first.GetButton().Bind(wx.EVT_SET_FOCUS, self.OnSelected)
        self.second.GetButton().Bind(wx.EVT_SET_FOCUS, self.OnSelected)

        self.group_id = group_id

    def destroy(self):
        """Destroy Header and footer containers"""

        self.first.Destroy()
        self.second.Destroy()

    def update_name(self):
        """Update group name from properties"""

        _name = self.get_value("group", "name")
        _titles = self.build_titles("Group '%s' " % _name, PAIR_TITLE_SUMMARY)
        self.first.set_title(_titles[0])
        self.second.set_title(_titles[1])

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if category == "group":
            self.update_name()
            self.report.synchronize_group(self)
