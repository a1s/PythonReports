"""Bind datatypes to property grid"""
#----------------------------Property Creation Methods-------------------------
def setup_value(prop, value):
    """Check value and add it to property"""
    if value is None:
        prop.SetValueToUnspecified()
    else:
        prop.SetValue(value)

def pack_prop_name(tag, label):
    """Return property wxpg name by label and tag"""
    return str((tag, label))

def unpack_prop_name(name):
    """Return tuple (tag and category of property by it's name"""
    _res = eval(name)
    if not isinstance(_res, tuple):
        raise ValueError("Invalid property name '%s'" % name)
    return _res

def c_simple(prop_grid, field_type, tag, label, value, param):
    """Create simple property field, for example int, float..."""
    _prop = prop_grid.Append(
        field_type(label, pack_prop_name(tag, label))
    )
    setup_value(_prop, value)
    return _prop

def c_bool(prop_grid, field_type, tag, label, value, param):
    """Create bool field. Additional checkbox element"""
    _prop = c_simple(prop_grid, field_type, tag, label, value, param)
    _prop.SetAttribute("UseCheckbox", True)
    return _prop

def c_enum(prop_grid, field_type, tag, label, value, param):
    """Enum fields. params is list of elements in enum"""
    _prop = prop_grid.Append(
        field_type(label, pack_prop_name(tag, label), labels=param)
    )
    setup_value(_prop, value)
    return _prop

def c_colour(prop_grid, field_type, tag, label, value, param={}):
    """Colour fields.

    @param param: dict of known colour constants binded with Hex colour value

    """
    def hex_to_color(hex_string):
        """Convert '#AABBCC' to wx.Color"""
        import wx
        _no_sharp = hex_string.__str__()[1:]
        import struct
        (_r, _g, _b) = struct.unpack("BBB", _no_sharp.decode("hex"))
        return wx.Colour(_r, _g, _b)

    _prop = prop_grid.Append(
        field_type(label, pack_prop_name(tag, label))
    )
    if value is None:
        _prop.SetValueToUnspecified()
    elif param.get(value):
        _prop.SetValue(param[value])
    else:
        #direct "#AABBCC" or tuple doesn't work in this place Oo
        _prop.SetValue(hex_to_color(value))
    return _prop

def c_list(prop_grid, field_type, tag, label, value, param={}):
    """List of properties"""
    return prop_grid.Append(
        field_type(value, prop_grid, label, pack_prop_name(tag, label))
    )

#----------------------------Back Conversion Functions-------------------------
def by_val(prop, res_type):
    """Use value from property"""
    if prop.GetValue() is None:
        return None
    return res_type(prop.GetValue())

def by_str(prop, res_type):
    """Use value as string"""
    if prop.GetValue() is None:
        return None
    return res_type(prop.GetValueAsString())

def by_color(prop, res_type):
    """Use value converted into RGB tuple"""
    if prop.GetValue() is None:
        return None
    return res_type(prop.GetValue().Get())

def by_dir(prop, res_type):
    """Directly return value form property"""
    return prop.GetValue()

#Settings of all PythonReports Datatypes
#1 - Default value if REQUIRED in Validator
#2 - Property field type name. Class object will be evaluated by "eval"
#3 - property field creation function
#4 - list of known elements <NAME> (for example for Enums), get it from type
#5 - conversion function, that converts wxpg Property to DATATYPE
DATATYPES_SETTINGS = {
    "Boolean": (True, "wx.propgrid.BoolProperty", c_bool, None, by_val),
    "Integer": (0, "wx.propgrid.IntProperty", c_simple, None, by_val),
    "Number": (0, "wx.propgrid.FloatProperty", c_simple, None, by_val),
    "_Number": (0, "wx.propgrid.FloatProperty", c_simple, None, by_val),
    "Dimension": (100, "wx.propgrid.FloatProperty", c_simple, None, by_val),
    "Color": ("BLACK", "wx.propgrid.ColourProperty", c_colour, "names", by_color),
    "String": ("default", "wx.propgrid.StringProperty", c_simple, None, by_val),
    "Expression": ("THIS", "wx.propgrid.StringProperty", c_simple, None, by_val),
    "AlignHorizontal": ("left", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "AlignVertical": ("bottom", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "BarCodeType": ("Code128", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "BitmapScale": ("cut", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "BitmapType": ("png", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "Calculation": ("count", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "Compress": ("zlib", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "EjectType": ("page", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "Encoding": ("base64", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "PageSize": ("A4", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "PenTypeExtended": ("1", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "TextAlignment": ("left", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "VariableIteration": ("detail", "wx.propgrid.EnumProperty", c_enum, "VALUES", by_str),
    "ListPropertyValue": (None, "propertiesgrid.ListProperty", c_list, None, by_dir),
    "XmlBody" : ("", "wx.propgrid.LongStringProperty", c_simple, None, by_val)
}

class SettingsRow(object):
    def __init__(self, row_tuple):
        self.default_value = row_tuple[0]
        self.property_class_string = row_tuple[1]
        self.prop_class = None
        self.creation_func = row_tuple[2]
        self.param = row_tuple[3]
        self.conversion_func = row_tuple[4]

    def evaluate_class(self):
        """Convert class string into property class object"""
        if self.prop_class:
            return self.prop_class

        _mod_name, _class_name = self.get_mod_class(self.property_class_string)
        _module = self.import_mod(_mod_name)
        self.prop_class = getattr(_module, _class_name)
        return self.prop_class

    def import_mod(self, module_name):
        """Import new module if doesn't exist"""
        import sys, types
        try:
            _module = sys.modules[module_name]
            if not isinstance(_module, types.ModuleType):
                raise KeyError
        except KeyError:
            # The last [''] is very important!
            _module = __import__(module_name, globals(), locals(), [''])
            sys.modules[module_name] = _module
        return _module

    def get_mod_class(self, class_string):
        """Convert class string into module name and class name"""

        try:
            dot = class_string.rindex(".")
        except ValueError:
            return None, class_string
        return class_string[:dot], class_string[dot + 1:]

DATATYPES_SETTINGS = dict((_key, SettingsRow(_row_tuple))
    for (_key, _row_tuple) in DATATYPES_SETTINGS.items())
