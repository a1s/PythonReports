"""Bind datatypes to property grid"""
"""
20-mar-2012 [kacah]   created

"""
import wx.propgrid as wxpg

def simple_field_create(prop_grid, field_type, name, value, params=None):
    """Create simple property field, for example int, float..."""
    prop_grid.Append(field_type(name, value=value))

def bool_field_create(prop_grid, field_type, name, value, params=None):
    """Create bool field. Additional checkbox element"""
    prop_grid.Append(field_type(name, value=value))
    prop_grid.SetPropertyAttribute(name, "UseCheckbox", True)

def enum_field_create(prop_grid, field_type, name, value, params=[]):
    """Enum fields. params is list of elements in enum """
    prop_grid.Append(field_type(name, name, labels=params,
        value=params.index(value)))

#Settings of all PythonReports Datatypes
#1 - Default for NONE, 2 - Default for REQUIRED, 3 - Property field type
#4 - property field creation function
DATATYPES_SETTINGS = {
    "Boolean" : (True, True, wxpg.BoolProperty, bool_field_create),
    "Integer" : (0, 0, wxpg.IntProperty, simple_field_create),
    "Number" : (0, 0, wxpg.FloatProperty, simple_field_create),
    "Dimension" : ("300", "100", wxpg.FloatProperty, simple_field_create),
    "Color" : ("BLACK", "BLACK", "", None),
    "String" : ("", "default", wxpg.StringProperty, simple_field_create),
    "Expression" : ("", "THIS", wxpg.StringProperty, simple_field_create),
    "AlignHorizontal" : ("left", "left", wxpg.EnumProperty, enum_field_create),
    "AlignVertical" : ("bottom", "bottom", wxpg.EnumProperty, enum_field_create),
    "BarCodeType" : ("Code128", "Code128", wxpg.EnumProperty, enum_field_create),
    "BitmapScale" : ("cut", "cut", wxpg.EnumProperty, enum_field_create),
    "BitmapType" : ("png", "png", wxpg.EnumProperty, enum_field_create),
    "Calculation" : ("count", "count", wxpg.EnumProperty, enum_field_create),
    "Compress" : ("zlib", "zlib", wxpg.EnumProperty, enum_field_create),
    "EjectType" : ("page", "page", wxpg.EnumProperty, enum_field_create),
    "Encoding" : ("base64", "base64", wxpg.EnumProperty, enum_field_create),
    "PageSize" : ("A4", "A4", wxpg.EnumProperty, enum_field_create),
    "PenType" : ("dot", "dot", wxpg.EnumProperty, enum_field_create),
    "TextAlignment" : ("left", "left", wxpg.EnumProperty, enum_field_create),
    "VariableIteration" :
        ("detail", "detail", wxpg.EnumProperty, enum_field_create),
}
