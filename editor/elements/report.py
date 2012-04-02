"""Main element, Root of template"""
"""
02-mar-2012 [kacah]    Added reaction on property change
20-mar-2012 [kacah]    created

"""
import PythonReports.template as te
from PythonReports import datatypes
import wx

from container import Container
from elements.element import Element
from section import Section
import sectioncontainer as seccon
import utils

DEFAULT_WIDTH = 500

REPORT_PREFIX = "Report "
PAGE_PREFIX = "Page "
DETAIL_NAME = "Detail"
REPORT_NAME = "Report"

MAIN_VALIDATOR = te.Report
ZERO_OR_ONE_VALIDATORS = [te.Columns]
ONE_VALIDATORS = [te.Layout]
UNRESTRICTED_VALIDATORS = [te.Parameter, te.Import, te.Variable, te.Font,
    te.Data, te.Style, te.Group]

class Report(Container, Element):
    """Main, Report element, Root of template"""

    def __init__(self, parent, prop_grid):
        Container.__init__(self, parent, REPORT_NAME, DEFAULT_WIDTH)
        Element.__init__(self, prop_grid,
            MAIN_VALIDATOR, ZERO_OR_ONE_VALIDATORS,
            ONE_VALIDATORS, UNRESTRICTED_VALIDATORS)

        self.GetButton().Bind(wx.EVT_SET_FOCUS, self.OnSelected)

        self.create_sections()
        self.update_layout()

    def create_sections(self):
        """Create general sections of the report
        
        * Create pair for title/summary
        * Create Columns
        * Create empty groups list
        * Create pair for header/footer
        * Create detail section
        
        """
        self.title_summary = seccon.SectionPair(self.GetPane(), self.prop_grid,
            DEFAULT_WIDTH, seccon.PAIR_TITLE_SUMMARY, REPORT_PREFIX)
        self.columns = seccon.Columns(self.GetPane(), self.prop_grid, \
            DEFAULT_WIDTH, self)
        self.groups = []
        self.header_footer = seccon.SectionPair(self.GetPane(), self.prop_grid,
            DEFAULT_WIDTH, seccon.PAIR_HEADER_FOOTER, PAGE_PREFIX)
        self.detail = Section(self.GetPane(), self.prop_grid, DETAIL_NAME,
            DEFAULT_WIDTH)

    def get_page_size(self):
        """Get page size (tuple - width, height) from properties"""

        _pagesize = self.get_value("layout", "pagesize")

        if _pagesize is None:
            _width = self.get_value("layout", "width")
            _height = self.get_value("layout", "height")
        else:
            (_width, _height) = datatypes.PageSize.DIMENSIONS[_pagesize]

        if self.get_value("layout", "landscape"):
            _width, _height = _height, _width

        if _width is None:
            _width = DEFAULT_WIDTH
        if _height is None:
            _height = DEFAULT_WIDTH

        return (_width, _height)

    def get_margins(self):
        """Get margins of page (tuple - top, right, bot, left) from properties"""

        return (
            self.get_value("layout", "topmargin"),
            self.get_value("layout", "rightmargin"),
            self.get_value("layout", "bottommargin"),
            self.get_value("layout", "leftmargin"),
        )

    def has_columns(self):
        """Determine if this report has columns"""
        return self.get_value("columns", self.EXISTANCE_PROPERTY)

    def update_layout(self):
        """Change size of work space, using properties['layout']"""

        self.detach_all()

        self.cur_width = utils.dim_to_screen(self.get_page_size()[0])
        self.set_width(self.cur_width)

        self.cur_pos = 0
        self._update_title_summary()
        self._update_columns()
        self._update_groups()
        self._update_header_footer()
        self._update_detail()

    def _insert_pair(self, pair, pos):
        """Insert sections pair into given position"""

        self.insert_element(pair.get_first(), pos)
        self.insert_element(pair.get_second(), pos + 1)

    def _update_pair(self, pair):
        """Update width and insert one pair"""

        pair.set_width(self.cur_width)
        self._insert_pair(pair, self.cur_pos)
        self.cur_pos += 1

    def _update_title_summary(self):
        """Update title and summary of the report"""

        (_top_m, _right_m, _bot_m, _left_m) = self.get_margins()
        self.cur_width -= \
            utils.dim_to_screen(_right_m) + utils.dim_to_screen(_left_m)

        self._update_pair(self.title_summary)

    def _update_columns(self):
        """Update columns if they are set in report"""

        if self.has_columns():
            _col_count = self.get_value("columns", "count")
            _col_gap = self.get_value("columns", "gap")
            self.cur_width = self.columns.count_width(self.cur_width,
                _col_count, _col_gap)

            self.columns.set_visible(True)
            self.columns.synchronize_attributes("columns", \
                self.get_category("columns"))
            self._update_pair(self.columns)
        else:
            self.columns.set_visible(False)

    def _get_group(self, id):
        """Get group with given id, or create new if doesn't exist"""

        res = None
        for _group in self.groups:
            if _group.group_id == id:
                res = _group
                break
        else:
            res = seccon.Group(self.GetPane(), self.prop_grid,
                DEFAULT_WIDTH, id, self)
        return res

    def _clear_groups(self, old_list, new_list):
        """Clear groups deleted by user from old list"""

        from sets import Set
        _old = Set(old_list)
        _new = Set(new_list)
        _diff = _old - _new

        for _group in _diff:
            _group.destroy()

    def _update_groups(self):
        """Update all groups of report"""

        _groups = self.get_value("lists", "group").get_all()
        _new_group_list = []
        for _group in _groups:
            _group_elem = self.__get_group(_group.id)
            _group_elem.synchronize_attributes("group", \
                _group.get_category("group"))
            _new_group_list.append(_group_elem)
            self._update_pair(_group_elem)

        self._clear_groups(self.groups, _new_group_list)
        self.groups = _new_group_list

    def _update_header_footer(self):
        """Update header and footer of the report"""

        self._update_pair(self.header_footer)

    def _update_detail(self):
        """Update detail of the report"""

        self.detail.set_width(self.cur_width)
        self.insert_element(self.detail, self.cur_pos)
        self.cur_pos += 1

    def synchronize_columns(self):
        """Get data from columns to self"""

        self.synchronize_attributes("columns",
            self.columns.get_category("columns"))

    def synchronize_group(self, group):
        """Get data from group to self"""

        _gr_value = self.get_value("lists", "group").get_by_id(group.group_id)
        _gr_value.synchronize_attributes("group", group.get_category("group"))

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if (category == "layout") or (category == "columns") \
        or (category == "lists" and attribute == "group"):
            self.update_layout()
