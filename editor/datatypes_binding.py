"""Bind datatypes to property grid"""
"""
20-mar-2012 [kacah]   created

"""
import wx.propgrid as wxpg

def setup_value(prop, value):
    """Check value anf add it to property"""
    if value is None:
        prop.SetValueToUnspecified()
    else:
        prop.SetValue(value)

def simple_field_create(prop_grid, field_type, name, value, params=None):
    """Create simple property field, for example int, float..."""
    _prop = prop_grid.Append(field_type(name))
    setup_value(_prop, value)
    return _prop

def bool_field_create(prop_grid, field_type, name, value, params=None):
    """Create bool field. Additional checkbox element"""
    _prop = simple_field_create(prop_grid, field_type, name, value, params)
    prop_grid.SetPropertyAttribute(name, wxpg.PG_BOOL_USE_CHECKBOX, True)
    return _prop

def enum_field_create(prop_grid, field_type, name, value, params=[]):
    """Enum fields. params is list of elements in enum"""
    _prop = prop_grid.Append(field_type(name, name, labels=params))
    setup_value(_prop, value)
    return _prop

def colour_field_create(prop_grid, field_type, name, value, params={}):
    """Colour fields. 
    
    @param params: dict of known colour constants binded with Hex colour value
    
    """
    if params.get(value):
        value = params[value]
    return prop_grid.Append(field_type(name, value=value.__str__()))

#Settings of all PythonReports Datatypes
#1 - Default valueif REQUIRED in Validator, 2 - Property field type
#3 - property field creation function
DATATYPES_SETTINGS = {
    "Boolean": (True, wxpg.BoolProperty, bool_field_create),
    "Integer": (0, wxpg.IntProperty, simple_field_create),
    "Number": (0, wxpg.FloatProperty, simple_field_create),
    "Dimension": (100, wxpg.FloatProperty, simple_field_create),
    "Color": ("BLACK", wxpg.ColourProperty, colour_field_create),
    "String": ("default", wxpg.StringProperty, simple_field_create),
    "Expression": ("THIS", wxpg.StringProperty, simple_field_create),
    "AlignHorizontal": ("left", wxpg.EnumProperty, enum_field_create),
    "AlignVertical": ("bottom", wxpg.EnumProperty, enum_field_create),
    "BarCodeType": ("Code128", wxpg.EnumProperty, enum_field_create),
    "BitmapScale": ("cut", wxpg.EnumProperty, enum_field_create),
    "BitmapType": ("png", wxpg.EnumProperty, enum_field_create),
    "Calculation": ("count", wxpg.EnumProperty, enum_field_create),
    "Compress": ("zlib", wxpg.EnumProperty, enum_field_create),
    "EjectType": ("page", wxpg.EnumProperty, enum_field_create),
    "Encoding": ("base64", wxpg.EnumProperty, enum_field_create),
    "PageSize": ("A4", wxpg.EnumProperty, enum_field_create),
    "PenType": ("dot", wxpg.EnumProperty, enum_field_create),
    "TextAlignment": ("left", wxpg.EnumProperty, enum_field_create),
    "VariableIteration": ("detail", wxpg.EnumProperty, enum_field_create),
}
