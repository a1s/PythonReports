"""Elements for working with Property Grid"""
"""
23-mar-2012 [kacah]    Added empty properties
20-mar-2012 [kacah]    created

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

    def update_property(self, changed_property):
        """Update property in dictionary by property grid's Property
        
        Parent is category of property
        
        """
        _tag = changed_property.GetParent().GetName()
        _attr = changed_property.GetName()

        _property_params = self.properties[_tag][_attr]
        (_value, _type, _default_value) = _property_params

        #TODO: May add check if property realy can be None
        if self.prop_grid.IsPropertyUnspecified(changed_property.GetName()):
            _value = None
        else:
            _value = _type(changed_property.GetValueAsString())
        self.properties[_tag][_attr] = (_value, _type, _default_value)

    def OnPropGridChange(self, event):
        """Change element state in parent"""

        _property = event.GetProperty()
        if _property:
            self.update_property(_property)

    def add_attributes(self, tag, attributes):
        """Add all attributes with values to properties dictionary"""

        self.properties[tag] = {}

        for _name, _params in attributes.items():
            _attr_class = _params[0]
            _default_value = _params[1]
            if _default_value is datatypes.REQUIRED:
                _default_value = datatypes_binding.DATATYPES_SETTINGS[
                    _attr_class.__name__][0]

            if _default_value is None:
                _value = None
            else:
                _value = _attr_class(_default_value)

            self.properties[tag][_name] = (_value, _attr_class, _default_value)


class PropertiesGrid(wxpg.PropertyGrid):
    """Display and allow to modify object settings"""

    class ClearMenu(wx.Menu):
        """Menu which allow to clear property"""

        def __init__(self):
            wx.Menu.__init__(self)

            self.property = None
            self.element = None

            _id = wx.NewId()
            _title = "Clear"
            _menu_item = self.Append(_id, _title)
            self.Bind(wx.EVT_MENU, self.OnEmptyMenu, _menu_item)

        def attach_property(self, attached_property):
            """Add property to change"""
            self.property = attached_property

        def attach_element(self, element):
            """Add element to change"""
            self.element = element

        def OnEmptyMenu(self, event):
            if self.property and self.element:
                self.property.SetValueToUnspecified()
                self.element.update_property(self.property)
            else:
                print "Error, Property on Element in menu not set"


    def __init__(self, parent):
        wxpg.PropertyGrid.__init__(self, parent, size=wx.Size(250, 600),
            style=wxpg.PG_SPLITTER_AUTO_CENTER | wxpg.PG_AUTO_SORT)

        self.element = None

        self.clear_menu = self.ClearMenu()
        self.Bind(wxpg.EVT_PG_RIGHT_CLICK, self.OnPropGridRightClick)

    def setup_by_element(self, element):
        """Setup properties by given element"""

        if self.element is element:
            return

        self.unsetup()

        if not getattr(element, "properties"):
            return

        self.element = element
        self.clear_menu.attach_element(element)
        self.Bind(wxpg.EVT_PG_CHANGED, element.OnPropGridChange)

        for _tag, _body in element.properties.items():
            self.append_atributes(_tag, _body)

    def unsetup(self):
        """Clear grid at remove link to element"""

        self.Clear()
        self.element = None
        self.clear_menu.attach_element(None)
        self.Unbind(wxpg.EVT_PG_CHANGED)

    def append_attribute(self, tag, name, _property_params):
        """Append PythonReports attribute to property bar"""

        (_value, _type, _default_value) = _property_params

        _attr_settings = datatypes_binding.DATATYPES_SETTINGS[_type.__name__]

        (_default_for_req, _field_type, _creation_function) = _attr_settings

        #try to get defined color constants for color type
        if issubclass(_type, datatypes.Color):
            _params = _type.names
        #try to get values from Code type, need for enum
        elif issubclass(_type, datatypes._Codes):
            _params = _type.VALUES
        else:
            _params = None

        _property = _creation_function(self, _field_type, name, _value, _params)
        #client data = if this property can be empty
        _property.SetClientData(_default_value is None)

    def append_atributes(self, tag, attributes):
        """Append list of PythonReports attributes to property bar"""

        self.Append(wxpg.PropertyCategory(tag))

        for _name, _property_params in attributes.items():
            self.append_attribute(tag, _name, _property_params)

    def OnPropGridRightClick(self, event):
        """Show ClearMenu, if property can be empty"""

        _property = event.GetProperty()
        if _property and _property.GetClientData():
            self.clear_menu.attach_property(_property)
            _pos = self.ScreenToClient(wx.GetMousePosition())
            self.PopupMenu(self.clear_menu, _pos)
