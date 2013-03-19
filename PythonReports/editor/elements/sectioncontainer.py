"""Classes for groups and columns"""

import PythonReports.template as te
from PythonReports import datatypes
import wx

from container import HeaderButton
from element import Element
from section import Section


PAIR_TITLE_SUMMARY = 0
PAIR_HEADER_FOOTER = 1
PAIR_TITLES = [("title", "summary"), ("header", "footer")]

class SectionPair(object):
    """Pair of header/footer of title/summary elements"""

    def __init__(self, parent, width, p_id, prefix="", has_head=False):
        """Create two section elements

        @param p_id: 0 - title, summary | 1 - header, footer
        @param prefix: string, prefix of titles

        """
        _titles = self.build_titles(prefix, p_id)

        self.head_btn = None
        self.first = Section(parent, _titles[0], width)
        self.second = Section(parent, _titles[1], width)

        if has_head:
            self.head_btn = HeaderButton(parent, prefix, width)

    def build_titles(self, prefix, p_id):
        """Build titles of pair by prefix and pair name id"""

        return (prefix + PAIR_TITLES[p_id][0], prefix + PAIR_TITLES[p_id][1])

    def has_head(self):
        """Get if this pair has head control"""
        return self.head_btn is not None

    def get_head(self):
        """Return head control of this pair"""
        return self.head_btn

    def highlight(self, need_hl):
        """Highlight this pair"""

        if self.has_head():
            self.head_btn.highlight(need_hl)

    def set_visible(self, visible):
        """Set both pair elements visible or not"""

        if self.has_head():
            self.head_btn.set_visible(visible)

        self.first.set_visible(visible)
        self.second.set_visible(visible)

    def set_width(self, width):
        """Set width of both pair elements"""

        if self.has_head():
            self.head_btn.set_width(width)

        self.first.set_width(width)
        self.second.set_width(width)

    def get_first(self):
        """Get first section of pair"""
        return self.first

    def get_second(self):
        """Get second element of pair"""
        return self.second

    def items(self):
        """Return a sequence containing both elements of the pair"""
        return (self.first, self.second)

    def force_data_update(self):
        """Update all elements that are linked to report data"""
        self.first.force_data_update()
        self.second.force_data_update()

    def update_height(self):
        """Update height for both sections"""
        self.first.update_height()
        self.second.update_height()


ColumnHeaders = datatypes.Validator(tag="headers",
    attributes={
        te.Header.tag: (datatypes.Boolean, True),
        te.Footer.tag: (datatypes.Boolean, True),
    }, doc="Show and hide headers and footers, only for internal editor use"
)

UNRESTRICTED_STYLE = [te.Style]
COLUMN_HEADERS = [ColumnHeaders]
MAIN_COLUMNS = te.Columns

COLUMN_PREFIX = "Column "

class Columns(SectionPair, Element):
    """PythonReports Columns element"""

    def __init__(self, parent, width, report):
        SectionPair.__init__(self, parent, width, PAIR_HEADER_FOOTER,
            COLUMN_PREFIX, True)
        Element.__init__(self, main_val=MAIN_COLUMNS, one_val=COLUMN_HEADERS,
            unrestricted_val=UNRESTRICTED_STYLE)

        self.head_btn.set_title("Columns")
        self.head_btn.Bind(wx.EVT_BUTTON, self.OnButton)

        self.report = report

    def OnButton(self, evt=None):
        wx.GetApp().focus_set(self)

    def count_width(self, width):
        """Count columns width by initial width and values from properties"""

        _col_count = self.get_value("columns", "count")
        _col_gap = self.get_value("columns", "gap")

        if _col_count < 1:
            _col_count = 1

        return width / _col_count - (_col_count - 1) * _col_gap

    def get_title(self):
        """Get title of columns pair"""

        return self.head_btn.get_title()

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if category == "columns":
            self.report.synchronize_columns()

        if category == "headers":
            self.report.update_layout()


GroupHeaders = datatypes.Validator(tag="headers",
    attributes={
        te.Title.tag: (datatypes.Boolean, True),
        te.Summary.tag: (datatypes.Boolean, True),
    }, doc="Show and hide headers and footers, only for internal editor use"
)

MAIN_GROUP = te.Group
GROUP_HEADERS = [GroupHeaders]
GROUP_PREFIX = "Group "

class Group(SectionPair, Element):
    """PythonReports Group element"""

    def __init__(self, parent, width, group_id, report):
        SectionPair.__init__(self, parent, width, PAIR_TITLE_SUMMARY,
            GROUP_PREFIX, True)
        Element.__init__(self, main_val=MAIN_GROUP, one_val=GROUP_HEADERS,
            unrestricted_val=UNRESTRICTED_STYLE)

        self.head_btn.set_title("Group")
        self.head_btn.Bind(wx.EVT_BUTTON, self.OnButton)

        self.id = group_id
        self.report = report

    def OnButton(self, evt=None):
        wx.GetApp().focus_set(self)

    def set_visible(self, visible):
        """Overrided from SectionPair"""

        SectionPair.set_visible(self, visible)
        self.head_btn.set_visible(visible)

    def get_title(self):
        """Get title of group pair"""

        return self.head_btn.get_title()

    def destroy(self):
        """Destroy Header and footer containers"""

        self.first.Destroy()
        self.second.Destroy()

    def update_name(self):
        """Update group name from properties"""

        _name = self.get_value("group", "name")
        _name = "Group '%s'" % _name
        _titles = self.build_titles(_name, PAIR_TITLE_SUMMARY)
        self.first.set_title(_titles[0])
        self.second.set_title(_titles[1])
        self.head_btn.set_title(_name)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if category == "group":
            self.update_name()
            self.report.synchronize_group(self)

        if category == "headers":
            self.report.update_layout()
