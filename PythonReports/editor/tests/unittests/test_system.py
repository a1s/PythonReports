"""System methods tests"""
"""
16-jun-2012 [als]   Fix resource paths
19-may-2012 [kacah] created
"""

import unittest

import PythonReports.datatypes as datatypes
import wx

import application as application
import utils


POINTS_IN_INCH = 72
KNOWN_DPI = [72.0, 96.0]


class TestUtils(unittest.TestCase):
    """Test utils module"""

    def setUp(self):
        self.app = application.EditorApplication()

    def tearDown(self):
        wx.CallAfter(self.app.Exit)
        self.app.MainLoop()

    def test_1_starting(self):
        """Test if application can be started

        @note: is setUp() witout error - test passed

        """
        pass

    def test_2_dpi(self):
        """Test screen DPI after utils setup"""

        FAIL_MESSAGE = "Getting system DPI seems not correct"

        _dpi = utils.PT_TO_PIX * POINTS_IN_INCH
        self.assertIn(_dpi, KNOWN_DPI, FAIL_MESSAGE)

    def test_3_convertion(self):
        """Test conversion between pixels and PythonReports dimension"""

        FAIL_MESSAGE = "Conversion between PythonReport dimension" \
            " and pixels doesn't work"

        _dim = datatypes.Dimension("10")
        _px = utils.dim_to_screen(_dim)
        _res = utils.screen_to_dim(_px)

        self.assertEqual(str(_res), str(_dim), FAIL_MESSAGE)

    def test_4_scale_bitmap(self):
        """Test scale of wx.Bitmap method"""

        FAIL_MESSAGE = "Bitmap scaling doesn't work"

        _bitmap = wx.Image(
             os.path.join(utils.get_resource_dir(), "test_image.jpg"),
             wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        _scaled_bitmap = utils.scale_bitmap(_bitmap, 20, 30)
        self.assertEqual(_scaled_bitmap.GetWidth(), 20, FAIL_MESSAGE)
        self.assertEqual(_scaled_bitmap.GetHeight(), 30, FAIL_MESSAGE)

    def test_5_rotate_bitmap(self):
        """Test rotate of wx.Bitmap method"""

        FAIL_MESSAGE = "Bitmap rotating doesn't work"

        _bitmap = wx.Image(
            os.path.join(utils.get_resource_dir(), "test_image.jpg"),
            wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        _width_before = _bitmap.GetWidth()
        _height_before = _bitmap.GetHeight()

        _rotated_bitmap = utils.rotate90_bitmap(_bitmap, True)
        self.assertEqual(_rotated_bitmap.GetWidth(),
            _height_before, FAIL_MESSAGE)
        self.assertEqual(_rotated_bitmap.GetHeight(),
            _width_before, FAIL_MESSAGE)


class TestTemplates(unittest.TestCase):
    """Test actions with PethonReports template files"""

    def setUp(self):
        self.app = application.EditorApplication()

    def tearDown(self):
        wx.CallAfter(self.app.Exit)
        self.app.MainLoop()

    def test_1_template_new(self):
        """Test creating new template"""

        self.app.report_new()

    def test_2_template_open(self):
        """Test template opening"""

        self.app.report_open("sakila.prt");

    def test_3_template_open_save(self):
        """Test template saving"""

        FAIL_MESSAGE = "Data lost while saving or opening files"

        self.app.report_open("sakila.prt")
        self.app.report_save("save1.prt")
        self.app.report_open("save1.prt")
        self.app.report_save("save2.prt")

        import filecmp
        self.assertTrue(filecmp.cmp("save1.prt", "save2.prt"), FAIL_MESSAGE)


if __name__ == "__main__":
    unittest.main()

# vim: set et sts=4 sw=4 :
