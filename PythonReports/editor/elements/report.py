"""Main element, Root of template"""
"""
02-apr-2012 [kacah]    Added reaction on property change
20-mar-2012 [kacah]    created

"""
import PythonReports.template as te
from PythonReports import datatypes
import wx

import sectioncontainer as seccon
from container import Container
from element import Element
from section import Section
from .. import utils


Headers = datatypes.Validator(tag="headers",
    attributes={
        te.Title.tag: (datatypes.Boolean, True),
        te.Summary.tag: (datatypes.Boolean, True),
        te.Header.tag: (datatypes.Boolean, True),
        te.Footer.tag: (datatypes.Boolean, True),
        "swapheader": (datatypes.Boolean, False),
        "swapfooter": (datatypes.Boolean, False),
    }, doc="Show, hide and swap headers and footers, only for internal editor use"
)


DEFAULT_WIDTH = 500

REPORT_PREFIX = "Report "
PAGE_PREFIX = "Page "
DETAIL_NAME = "Detail"
REPORT_NAME = "Report"

MAIN_VALIDATOR = te.Report
ZERO_OR_ONE_VALIDATORS = [te.Columns]
ONE_VALIDATORS = [te.Layout, Headers]
UNRESTRICTED_VALIDATORS = [te.Parameter, te.Import, te.Variable, te.Font,
    te.Data, te.Style, te.Group]

class Report(Container, Element):
    """Main, Report element, Root of template"""

    def __init__(self, parent, page):
        Container.__init__(self, parent, REPORT_NAME, DEFAULT_WIDTH)
        Element.__init__(self, MAIN_VALIDATOR, ZERO_OR_ONE_VALIDATORS,
            ONE_VALIDATORS, UNRESTRICTED_VALIDATORS)

        self.page = page

        #list of all property listeners in this report
        self.listeners_list = []

        self.GetButton().Bind(wx.EVT_BUTTON, self.OnFocus)

        self.create_sections()
        self.update_layout()

    def OnFocus(self, evt=None):
        wx.GetApp().focus_set(self)

    def create_sections(self):
        """Create general sections of the report

        * Create pair for title/summary
        * Create Columns
        * Create empty groups list
        * Create pair for header/footer
        * Create detail section

        """
        self.title_summary = seccon.SectionPair(self.GetPane(),
            DEFAULT_WIDTH, seccon.PAIR_TITLE_SUMMARY, REPORT_PREFIX)
        self.columns = seccon.Columns(self.GetPane(), DEFAULT_WIDTH, self)
        self.groups = []
        self.header_footer = seccon.SectionPair(self.GetPane(), DEFAULT_WIDTH,
           seccon.PAIR_HEADER_FOOTER, PAGE_PREFIX)
        self.detail = Section(self.GetPane(), DETAIL_NAME, DEFAULT_WIDTH)

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

    #Just add this value to width to fix rounding and +-1 errors
    WIDTH_ROUND_FIX = 1

    def update_layout(self):
        """Change size of work space, using properties['layout']"""

        self.detach_all()
        self.listeners_list = []

        self.cur_width = utils.dim_to_screen(self.get_page_size()[0])
        (_top_m, _right_m, _bot_m, _left_m) = self.get_margins()
        self.cur_width -= \
            utils.dim_to_screen(_right_m) + utils.dim_to_screen(_left_m)

        self.cur_width += self.WIDTH_ROUND_FIX

        self.set_width(self.cur_width)

        self.cur_pos = 0
        self._update_headers()
        self._update_columns()
        self._update_groups()
        self._update_detail()
        wx.GetApp().elemtree_update_report()

    def _insert_two_headers(self, first, second, has_first, has_second):
        """Insert two headers and set pointer on next element between them"""

        if has_first:
            self.insert_element(first, self.cur_pos)
            self.listeners_list.insert(self.cur_pos, first)
            self.cur_pos += 1
        first.set_visible(has_first)

        if has_second:
            self.insert_element(second, self.cur_pos)
            self.listeners_list.insert(self.cur_pos, second)
        second.set_visible(has_second)

    def _update_pair(self, pair, has_first=True, has_second=True):
        """Update width and insert one pair"""

        pair.set_width(self.cur_width)

        LEFT_OFFSET = 3

        if pair.has_head():
            self.listeners_list.insert(self.cur_pos, pair)
            self.insert_element(pair.get_head(), self.cur_pos, LEFT_OFFSET)
            self.cur_pos += 1

        self._insert_two_headers(pair.get_first(), pair.get_second(),
            has_first, has_second)

    def _update_headers(self):
        """Update title and summary of the report"""

        self.title_summary.set_width(self.cur_width)
        self.header_footer.set_width(self.cur_width)

        #create tuples for all header 1 - header element, 2 - visibility
        _header = (self.header_footer.get_first(),
            self.get_value("headers", "header"))
        _footer = (self.header_footer.get_second(),
            self.get_value("headers", "footer"))
        _title = (self.title_summary.get_first(),
            self.get_value("headers", "title"))
        _summary = (self.title_summary.get_second(),
            self.get_value("headers", "summary"))

        _head_seq = [_header, _title, _summary, _footer]

        #swap elements in list if necessary
        if self.get_value("headers", "swapheader"):
            _head_seq[0], _head_seq[1] = _head_seq[1], _head_seq[0]
        if self.get_value("headers", "swapfooter"):
            _head_seq[2], _head_seq[3] = _head_seq[3], _head_seq[2]

        #insert first and last tuples (see tuple struct above)
        self._insert_two_headers(_head_seq[0][0], _head_seq[3][0],
            _head_seq[0][1], _head_seq[3][1])
        #insert middle tuples (see tuple struct above)
        self._insert_two_headers(_head_seq[1][0], _head_seq[2][0],
            _head_seq[1][1], _head_seq[2][1])

    def _update_columns(self):
        """Update columns if they are set in report"""

        if self.has_columns():
            self.columns.synchronize_attributes("columns", \
                self.get_category("columns"))

            self.cur_width = self.columns.count_width(self.cur_width)

            self._update_pair(self.columns,
                self.columns.get_value("headers", "header"),
                self.columns.get_value("headers", "footer"))

            self.columns.set_visible(True)
        else:
            self.columns.set_visible(False)

    def _create_group(self, id):
        """Create group with given id"""

        return seccon.Group(self.GetPane(), DEFAULT_WIDTH, id, self)

    def _update_group(self, group):
        """Update one group element"""

        group.update_name()
        self._update_pair(group,
            group.get_value("headers", "title"),
            group.get_value("headers", "summary"))

    def _update_groups(self):
        """Update all groups of report"""

        _new_groups = self.synchronize_list_category("group", self.groups,
            self._create_group, self._update_group)
        utils.destroy_difference(self.groups, _new_groups)
        self.groups = _new_groups

    def _update_detail(self):
        """Update detail of the report"""

        self.detail.set_width(self.cur_width)
        self.insert_element(self.detail, self.cur_pos)
        self.listeners_list.insert(self.cur_pos, self.detail)
        self.cur_pos += 1

    def synchronize_columns(self):
        """Get data from columns to self"""

        self.synchronize_attributes("columns",
            self.columns.get_category("columns"))

    def synchronize_group(self, group):
        """Get data from group to self"""

        _gr_value = self.get_value("lists", "group").get_by_id(group.id)
        _gr_value.synchronize_attributes("group", group.get_category("group"))

    def update_data(self):
        """Update all elements that use data and basedir"""

        self.title_summary.force_data_update()
        self.columns.force_data_update()
        for _group in self.groups:
            _group.force_data_update()
        self.header_footer.force_data_update()
        self.detail.force_data_update()

    def update_sections_height(self):
        """Update all sections height"""

        self.title_summary.update_height()
        self.columns.update_height()
        for _group in self.groups:
            _group.update_height()
        self.header_footer.update_height()
        self.detail.update_height()

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if (category == "layout") or (category == "columns") \
        or (category == "lists" and attribute == "group") \
        or (category == "headers"):
            self.update_layout()

        if (category == "layout"):
            self.page.update_margins()

        if (category == "lists" and attribute == "data") \
        or (attribute == "basedir"):
            self.update_data()
