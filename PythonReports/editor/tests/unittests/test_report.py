"""Report methods tests"""
"""
19-may-2012 [kacah] created

"""
import unittest

import PythonReports.datatypes as datatypes
import wx

import application as application
import utils


class TestReport(unittest.TestCase):
    """Test Report and its sections"""

    def setUp(self):
        self.app = application.EditorApplication()

        self.app.report_new()
        self.report = self.app.frame.workspace.get_report()
        
    def tearDown(self):
        wx.CallAfter(self.app.Exit)
        self.app.MainLoop()
    
    def __has_section(self, section_name):
        """Check if report has section with given name"""

        for _section in self.report.listeners_list:
            if _section.get_title() == section_name:
                return True

        return False

    def test_1_columns(self):
        """Test adding columns to report"""

        FAIL_MESSAGE = "Can't add columns into report"

        self.report.set_value("columns", "count", datatypes.Integer(2))
        self.report.set_value("columns", "__enabled", datatypes.Boolean(True))

        self.assertTrue(self.__has_section("Columns"), FAIL_MESSAGE)

    def test_2_add_group(self):
        """Test adding group into report"""

        FAIL_MESSAGE = "Can't add group into report"

        _group_list_value = self.report.get_value("lists", "group")
        _group_list_value.add()
        _group = _group_list_value.get(0)
        _group.set_value("group", "name", datatypes.String("Test Group"))

        self.assertTrue(self.__has_section("Group 'Test Group'"), FAIL_MESSAGE)

    def test_3_remove_group(self):
        """Test removing group into report"""

        FAIL_MESSAGE = "Can't remove group from report"

        _group_list_value = self.report.get_value("lists", "group")
        _group_list_value.add()
        _group = _group_list_value.get(0)
        _group.set_value("group", "name", datatypes.String("Test Group"))
        _group_list_value.remove(0)

        self.assertFalse(self.__has_section("Group 'Test Group'"), FAIL_MESSAGE)

    def test_4_remove_headers(self):
        """Test removing headers from report"""

        FAIL_MESSAGE = "Headers removing doesn't work"

        self.report.set_value("headers", "header", datatypes.Boolean(False))
        self.report.set_value("headers", "footer", datatypes.Boolean(False))
        self.report.set_value("headers", "title", datatypes.Boolean(False))
        self.report.set_value("headers", "summary", datatypes.Boolean(False))

        self.assertFalse(self.__has_section("Page header"), FAIL_MESSAGE)
        self.assertFalse(self.__has_section("Page footer"), FAIL_MESSAGE)
        self.assertFalse(self.__has_section("Report title"), FAIL_MESSAGE)
        self.assertFalse(self.__has_section("Report summary"), FAIL_MESSAGE)

    def test_5_resize(self):
        """Test report resizing"""

        FAIL_MESSAGE = "Report resizing doesn't work"

        _new_size = datatypes.Dimension(300)
        self.report.set_value("layout", "width", _new_size)
        _pix_size = utils.dim_to_screen(_new_size)
        self.assertAlmostEqual(_pix_size, self.report.GetSize()[0],
            msg=FAIL_MESSAGE, delta=10)

    def test_6_margins(self):
        """Test report margins"""

        FAIL_MESSAGE = "Report margins don't work"

        _rep_size = datatypes.Dimension(300)
        self.report.set_value("layout", "width", _rep_size)
        _margin_size = datatypes.Dimension(10)
        self.report.set_value("layout", "leftmargin", _margin_size)
        self.report.set_value("layout", "rightmargin", _margin_size)

        _pix_rep_size = utils.dim_to_screen(_rep_size)
        _pix_margin_size = utils.dim_to_screen(_margin_size)

        self.assertAlmostEqual(_pix_rep_size - 2*_pix_margin_size,
            self.report.GetSize()[0],  msg=FAIL_MESSAGE, delta=10)

    def test_7_add_data(self):
        """Test data objects adding"""

        FAIL_MESSAGE = "Data objects don't work"

        _data_list_value = self.report.get_value("lists", "data")
        _data_list_value.add()
        _data = _data_list_value.get(0)
        _data.set_value("data", "name", datatypes.String("Test Data"))

        self.assertIsNotNone(self.app.get_predefined_data("Test Data"),
            FAIL_MESSAGE)


if __name__ == "__main__":
    unittest.main()
