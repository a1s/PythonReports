"""Elements for working with Property Grid"""
"""
20-mar-2012 [kacah]   created

"""
import PythonReports.datatypes as datatypes
import wx
import wx.propgrid as wxpg

import datatypes_binding

class PropertiesListener(object):
    """Listen while control get or lost focus and update property grid
    
    @note: Inherit from this class your Element and BIND methods OnSetFocus
        and OnKillFocus to wx Events or something else
    
    """
    def __init__(self, prop_grid):
        self.prop_grid = prop_grid

        #attributes and child validated elements
        self.properties = {}

    def OnSetFocus(self, evt=None):
        self.prop_grid.setup_by_element(self)

    def OnPropGridChange(self, event):
        """Change element state in parent"""
        p = event.GetProperty()
        if p:
            print('%s changed to "%s"' % (p.GetName(), p.GetValueAsString()))

    def update_attributes(self, tag, attributes):
        """Add all attributes with values to tag"""
        self.properties[tag] = {}

        for _name, _params in attributes.items():
            _attr_class = _params[0]
            _value = _params[1]
            if _value is None:
                _value = datatypes_binding.DATATYPES_SETTINGS[
                    _attr_class.__name__][0]
            if _value is datatypes.REQUIRED:
                _value = datatypes_binding.DATATYPES_SETTINGS[
                    _attr_class.__name__][1]
            self.properties[tag][_name] = _attr_class(_value)


class PropertiesGrid(wxpg.PropertyGrid):
    """Display and allow to modify object settings"""

    def __init__(self, parent):
        wxpg.PropertyGrid.__init__(self, parent, size=wx.Size(250, 600),
            style=wxpg.PG_SPLITTER_AUTO_CENTER | wxpg.PG_AUTO_SORT)

        self.element = None

    def setup_by_element(self, element):
        """Setup properties by given element"""

        if self.element is element:
            return

        self.unsetup()

        if not getattr(element, "properties"):
            return

        self.element = element
        self.Bind(wxpg.EVT_PG_CHANGED, element.OnPropGridChange)

        for _tag, _body in element.properties.items():
            self.append_atributes(_tag, _body)

    def unsetup(self):
        """Clear grid at remove link to element"""

        self.Clear()
        self.element = None
        self.Unbind(wxpg.EVT_PG_CHANGED)

    def append_attribute(self, tag, name, value):
        """Append PythonReports attribute to property bar"""

        _type = value.__class__

        _attr_settings = datatypes_binding.DATATYPES_SETTINGS[_type.__name__]

        _field_type = _attr_settings[2]
        _creation_function = _attr_settings[3]
        _value = self.element.properties[tag][name]
        #try to get values from Code types, need for enum
        if isinstance(value, datatypes._Codes):
            _values_list = getattr(_type, "VALUES")
        else:
            _values_list = None

        _creation_function(self, _field_type, name, value, _values_list)

    def append_atributes(self, tag, attributes):
        """Append list of PythonReports attributes to property bar"""

        self.Append(wxpg.PropertyCategory(tag))

        for _name, _value in attributes.items():
            self.append_attribute(tag, _name, _value)
