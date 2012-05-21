"""Properties methods tests"""
"""
19-may-2012 [kacah] created

"""
import unittest

import PythonReports.datatypes as datatypes
import PythonReports.template as te
import wx

import application as application
from elements.element import XmlBody, PenTypeExtended
import propertiesgrid as pg


#property types for testing
#1 - type of property
#2 - init value
#3 - change value
TYPES = {
    "Boolean": (datatypes.Boolean, False, True),
    "Integer": (datatypes.Integer, 1, 15),
    "Number": (datatypes.Number, 1.5, 5.5),
    "Dimension": (datatypes.Dimension, "1pt", "3cm"),
    "Color": (datatypes.Color, "BLACK", "#123412"),
    "String": (datatypes.String, "StringInit", "StringChanged"),
    "Expression": (datatypes.Expression, "ExprInit", "ExprChanged"),
    "AlignHorizontal": (datatypes.AlignHorizontal, "left", "right"),
    "AlignVertical": (datatypes.AlignVertical, "bottom", "top"),
    "BarCodeType": (datatypes.BarCodeType, "Code128", "2of5i"),
    "BitmapScale": (datatypes.BitmapScale, "cut", "grow"),
    "BitmapType": (datatypes.BitmapType, "png", "gif"),
    "Calculation": (datatypes.Calculation, "count", "min"),
    "Compress": (datatypes.Compress, "zlib", "bz2"),
    "EjectType": (datatypes.EjectType, "page", "column"),
    "Encoding": (datatypes.Encoding, "base64", "qp"),
    "PageSize": (datatypes.PageSize, "A4", "EnvelopeA7"),
    "PenTypeExtended": (PenTypeExtended, "1", "dashdot"),
    "TextAlignment": (datatypes.TextAlignment, "left", "justified"),
    "VariableIteration": (datatypes.VariableIteration, "detail", "report"),
    "XmlBody": (XmlBody, "DataInit", "DataChanged"),
    "Unicode": (datatypes.String, u"Unīīīcodēēē", u"āāīīššš"),
}


class TestPropertiesListener(unittest.TestCase):
    """Test methods of PropertiesListener"""

    def setUp(self):
        self.p_listener = pg.PropertiesListener()

    def __test_property(self, tag, category, add_func, init_value="NoneNone"):
        """Adding all properties to given category

        @param add_func: function from PropertiesListener, that adds property
        @param init_value: initial value of all properties. If "NoneNone" will
                           be taken from TYPES

        """
        ADD_FAIL_MESSAGE = "Fail adding property %s with init value %s"
        CHANGE_FAIL_MESSAGE = "Fail changing property %s"

        _auto_value = init_value == "NoneNone"

        for (_type, _type_data) in TYPES.items():
            if _auto_value:
                init_value = _type_data[1]

            _attributes = {
                _type: (_type_data[0], init_value),
            }
            add_func(tag, _attributes)
            self.assertTrue(self.p_listener.has_value(category, _type),
                ADD_FAIL_MESSAGE % (_type, unicode(init_value)))

            _new_value = _type_data[0](_type_data[2])
            self.p_listener.set_value(category, _type, _new_value)
            self.assertEqual(self.p_listener.get_value(category, _type),
                _new_value, CHANGE_FAIL_MESSAGE % _type)

    def test_1_property_one(self):
        """Test ONE property"""

        self.__test_property("one", "one", self.p_listener.add_attr_ONE)

    def test_2_property_zero_or_one(self):
        """Test ZERO_OR_ONE property"""

        self.__test_property("zero_or_one", "zero_or_one",
            self.p_listener.add_attr_ZERO_OR_ONE)
        self.assertTrue(self.p_listener.has_value("zero_or_one",
            pg.PropertiesListener.EXISTANCE_PROPERTY))

    def test_3_property_unrestricted(self):
        """Test UNRESTRICTED property"""

        for (_type, _type_data) in TYPES.items():
            _attributes = {
                _type: (_type_data[0], _type_data[1]),
            }
            self.p_listener.add_attr_UNRESTRICTED(_type, _attributes)
            self.assertTrue(self.p_listener.has_value(
                pg.PropertiesListener.LIST_CATEGORY, _type))

    def test_4_property_required(self):
        """Test REQUIRED property"""

        self.__test_property("req", "req", self.p_listener.add_attr_ONE,
            datatypes.REQUIRED)

    def test_5_property_none(self):
        """Test NONE property"""

        self.__test_property("none", "none", self.p_listener.add_attr_ONE, None)

class TestPropertiesGrid(unittest.TestCase):
    """Test methods of PropertiesGrid"""

    def setUp(self):
        self.app = application.EditorApplication()

        self.p_listener = pg.PropertiesListener()

        for (_type, _type_data) in TYPES.items():
            _attributes = {
                _type: (_type_data[0], _type_data[1]),
            }
            self.p_listener.add_attr_ONE("test", _attributes)
            
    def tearDown(self):
        wx.CallAfter(self.app.Exit)
        self.app.MainLoop()
        
    def test_1_setup_by_element(self):
        """Test property grid initialization by PropertyListener"""

        self.app.frame.property_grid.setup_by_element(self.p_listener)

    def test_2_unsetup(self):
        """Test property grid clear up"""

        self.app.frame.property_grid.unsetup()


if __name__ == "__main__":
    unittest.main()
