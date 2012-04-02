"""Main element, Root of template"""
"""
20-mar-2012 [kacah]   created

"""
import PythonReports.template as te
import PythonReports.datatypes as datatypes
import wx

from container import Container
from elements.element import Element
from section import Section
import sectioncontainer as seccon
import utils

DEFAULT_WIDTH = 500

MAIN_VALIDATOR = te.Report
ZERO_OR_ONE_VALIDATORS = [te.Columns]
ONE_VALIDATORS = [te.Layout]
UNRESTRICTED_VALIDATORS = [te.Parameter, te.Import, te.Variable, te.Font,
    te.Data, te.Style, te.Group]

class Report(Container, Element):
    """Main, Report element, Root of template"""

    def __init__(self, parent, prop_grid):
        Container.__init__(self, parent, "Report", DEFAULT_WIDTH)
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
            DEFAULT_WIDTH, seccon.PAIR_TITLE_SUMMARY, "Report ")
        self.columns = seccon.Columns(self.GetPane(), self.prop_grid, \
            DEFAULT_WIDTH)
        self.groups = []
        self.header_footer = seccon.SectionPair(self.GetPane(), self.prop_grid,
            DEFAULT_WIDTH, seccon.PAIR_HEADER_FOOTER, "Report ")
        self.detail = Section(self.GetPane(), self.prop_grid, "Detail",
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
        self.__update_title_summary()
        self.__update_columns()
        self.__update_groups()
        self.__update_header_footer()
        self.__update_detail()

    def __insert_pair(self, pair, pos):
        """Insert sections pair into given position"""

        self.insert_element(pair.get_first(), pos)
        self.insert_element(pair.get_second(), pos + 1)

    def __update_pair(self, pair):
        """Update width and insert one pair"""

        pair.set_width(self.cur_width)
        self.__insert_pair(pair, self.cur_pos)
        self.cur_pos += 1

    def __update_title_summary(self):
        """Update title and summary of the report"""

        (_top_m, _right_m, _bot_m, _left_m) = self.get_margins()
        self.cur_width -= \
            utils.dim_to_screen(_right_m) + utils.dim_to_screen(_left_m)

        self.__update_pair(self.title_summary)

    def __update_columns(self):
        """Update columns if they are set in report"""

        if self.has_columns():
            _col_count = self.get_value("columns", "count")
            _col_gap = self.get_value("columns", "gap")
            self.cur_width = self.columns.count_width(self.cur_width,
                _col_count, _col_gap)

            self.columns.set_visible(True)
            self.__update_pair(self.columns)
        else:
            self.columns.set_visible(False)

    def __get_group(self, id):
        """Get group with given id, or create new if doesn't exist"""

        res = None
        for _group in self.groups:
            if _group.group_id == id:
                res = _group
                break
        else:
            res = seccon.Group(self.GetPane(), self.prop_grid,
                DEFAULT_WIDTH, id)
        return res

    def __clear_groups(self, old_list, new_list):
        """Clear groups deleted by user from old list"""

        from sets import Set
        _old = Set(old_list)
        _new = Set(new_list)
        _diff = _old - _new

        for _group in _diff:
            _group.destroy()

    def __update_groups(self):
        """Update all groups of report"""

        _groups = self.get_value("lists", "group").get_all()
        _new_group_list = []
        for _group in _groups:
            _group_elem = self.__get_group(_group.id)
            _group_elem.set_group_name(_group.get_value("group", "name"))
            _new_group_list.append(_group_elem)
            self.__update_pair(_group_elem)

        self.__clear_groups(self.groups, _new_group_list)
        self.groups = _new_group_list

    def __update_header_footer(self):
        """Update header and footer of the report"""

        self.__update_pair(self.header_footer)

    def __update_detail(self):
        """Update detail of the report"""

        self.detail.set_width(self.cur_width)
        self.insert_element(self.detail, self.cur_pos)
        self.cur_pos += 1

    def after_property_changed(self, category, attribute):
        """Change view after properties updated
        
        Overrided from PropertiesListener, do not need direct call.
        
        """
        if (category == "layout") or (category == "columns") \
        or (category == "lists" and attribute == "group"):
            self.update_layout()
