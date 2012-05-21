"""Section methods tests"""
"""
19-may-2012 [kacah] created

"""
import unittest

import PythonReports.datatypes as datatypes
import wx

import application as application
from elements.design import DESIGN_TOOLS
import utils


class TestSection(unittest.TestCase):
    """Test for one section and it's elements"""
    
    def setUp(self):
        self.app = application.EditorApplication()

        self.app.report_new()
        self.section = self.app.frame.workspace.get_report().detail
        self.section.Expand()
        
    def tearDown(self):
        wx.CallAfter(self.app.Exit)
        self.app.MainLoop()
    
    def test_1_section_resize(self):
        """Test resizing of section"""
        
        FAIL_MESSAGE = "Section resizing doesn't work"

        _new_size = datatypes.Dimension(200)
        self.section.set_value("box", "height", _new_size)
        
        _pix_size = utils.dim_to_screen(_new_size)
        self.assertEqual(_pix_size, self.section.design_place.GetSize()[1])
        
    def test_2_subreport(self):
        """Test adding subreports"""
        
        FAIL_MESSAGE = "Can't add subreport into report"

        _sub_list_value = self.section.get_value("lists", "subreport")
        _sub_list_value.add()
        _sub = _sub_list_value.get(0)
        _sub.set_value("subreport", "template", datatypes.String("Test Sub"))

        self.assertEqual(len(self.section.subreports), 1, FAIL_MESSAGE)
        
    def __test_creation(self, element_type):
        """Create one element with gven type and check it"""
        
        FAIL_MESSAGE = "Can't create " + element_type
        
        self.app.design_tool_set(DESIGN_TOOLS[element_type])
        self.section.design_place.OnLeftClick(10, 10, 0)
        
        _shapes_count = len(self.section.design_place.get_all_shapes())
        self.assertEqual(_shapes_count, 1, FAIL_MESSAGE)
        
    def test_3_create_field(self):
        """Test field creation"""
        self.__test_creation("Field")
        
    def test_4_create_line(self):
        """Test line creation"""  
        self.__test_creation("Line")
        
    def test_5_create_rectangle(self):
        """Test rectangle creation"""
        self.__test_creation("Rectangle")
        
    def test_6_create_image(self):
        """Test image creation"""
        self.__test_creation("Image")
        
    def test_7_create_barcode(self):
        """Test barcode creation"""
        self.__test_creation("Barcode")
        
    def test_8_delete_element(self):
        """Test element deleting"""
        
        FAIL_MESSAGE = "Can't delete element"
        
        self.app.design_tool_set(DESIGN_TOOLS["Field"])
        self.section.design_place.OnLeftClick(10, 10, 0)
        self.app.focus_delete()
        
        _shapes_count = len(self.section.design_place.get_all_shapes())
        self.assertEqual(_shapes_count, 0, FAIL_MESSAGE)
        
    def test_9_auto_size(self):
        """Test section adjusting to elements"""
        
        FAIL_MESSAGE = "Can't adjust section to elements"
        
        self.app.design_tool_set(DESIGN_TOOLS["Field"])
        self.section.design_place.OnLeftClick(10, 10, 0)
        self.section.set_value("box", "height", datatypes.Dimension(-1))
        
        _element = self.section.design_place.get_all_shapes()[0]
        
        #'10 + 'cause of element is at position (10, 10)
        self.assertEqual(10 + _element.GetHeight(), 
            self.section.design_place.GetSize()[1])
        
if __name__ == "__main__":
    unittest.main()
