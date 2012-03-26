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
        
        @note: Parent = category
        
        """
        _cat = changed_property.GetParent().GetName()
        _attr = changed_property.GetName()

        _property_params = self.properties[_cat][_attr]
        (_value, _type, _default_value) = _property_params

        _conversion_function = \
            datatypes_binding.DATATYPES_SETTINGS[_type.__name__].conversion_func
        _value = _conversion_function(changed_property, _type)
        self.properties[_cat][_attr] = (_value, _type, _default_value)

    def OnPropGridChange(self, event):
        """Change element state in parent"""

        _property = event.GetProperty()
        if _property:
            self.update_property(_property)

    def add_attr_ONE(self, tag, attributes):
        """Add attributes that always exist"""

        self.properties[tag] = {}

        for _name, _params in attributes.items():
            _attr_class = _params[0]
            _default_value = _params[1]

            _value = _default_value
            if _value is datatypes.REQUIRED:
                _value = datatypes_binding.DATATYPES_SETTINGS[
                    _attr_class.__name__].default_value
            elif _value is None:
                pass
            else:
                _value = _attr_class(_value)

            self.properties[tag][_name] = (_value, _attr_class, _default_value)

    EXISTANCE_PROPERTY = "__enabled"

    def add_attr_ZERO_OR_ONE(self, tag, attributes):
        """Add attributes that may not exist"""
        self.add_attr_ONE(tag, attributes)
        self.properties[tag][self.EXISTANCE_PROPERTY] = \
            (datatypes.Boolean(False), datatypes.Boolean, False)

    LIST_CATEGORY = "lists"

    def add_attr_UNRESTRICTED(self, tag, attributes):
        """Add attributes that can be many"""
        #create category for all unrestricted properties
        if not self.properties.get(self.LIST_CATEGORY):
            self.properties[self.LIST_CATEGORY] = {}

        _prop = ListPropertyValue([], tag, attributes)
        self.properties[self.LIST_CATEGORY][tag] = \
            (_prop, ListPropertyValue, [])


    def add_attributes(self, tag, attributes, attr_type):
        """Add all attributes with values to properties dictionary
        
        @param attr_type: ONE, ZERO_OR_ONE or UNRESTRICTED
        
        """
        if attr_type == datatypes.Validator.ONE:
            self.add_attr_ONE(tag, attributes)
        elif attr_type == datatypes.Validator.ZERO_OR_ONE:
            self.add_attr_ZERO_OR_ONE(tag, attributes)
        elif attr_type == datatypes.Validator.UNRESTRICTED:
            self.add_attr_UNRESTRICTED(tag, attributes)


class PropertiesGrid(wxpg.PropertyGrid):
    """Display and allow to modify object settings"""

    class ClearMenu(wx.Menu):
        """Menu which allow to clear property"""

        def __init__(self, prop_grid):
            wx.Menu.__init__(self)

            self.property = None
            self.prop_grid = prop_grid

            _id = wx.NewId()
            _title = "Clear"
            _menu_item = self.Append(_id, _title)
            self.Bind(wx.EVT_MENU, self.OnEmptyMenu, _menu_item)

        def attach_to_property(self, attached_property):
            """Add property to change"""
            self.property = attached_property

        def OnEmptyMenu(self, event):
            if self.property:
                self.property.SetValueToUnspecified()
                self.prop_grid.fire_property_update(self.property)
            else:
                print "Error, Property on Element in menu not set"


    def __init__(self, parent):
        wxpg.PropertyGrid.__init__(self, parent, size=wx.Size(250, 600),
            style=wxpg.PG_SPLITTER_AUTO_CENTER | wxpg.PG_AUTO_SORT)

        self.element = None

        self.clear_menu = self.ClearMenu(self)
        self.Bind(wxpg.EVT_PG_RIGHT_CLICK, self.OnPropGridRightClick)

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

    def append_attribute(self, tag, name, _property_params):
        """Append PythonReports attribute to property bar"""

        (_value, _type, _default_value) = _property_params

        _attr_settings = datatypes_binding.DATATYPES_SETTINGS[_type.__name__]

        _field_class = _attr_settings.evaluate_class()
        #get parameter value from type
        _param = None
        if _attr_settings.param:
            _param = getattr(_type, _attr_settings.param)

        _property = _attr_settings.creation_func(self, _field_class, name,
            _value, _param)
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
            self.clear_menu.attach_to_property(_property)
            _pos = self.ScreenToClient(wx.GetMousePosition())
            self.PopupMenu(self.clear_menu, _pos)

    def fire_property_update(self, prop):
        """Update property to element"""
        if self.element:
            self.element.update_property(prop)


class ListPropertyDialog(wx.Dialog):
    """Dialog for editing ListProperties"""

    DIALOG_SIZE = (400, 300)

    def __init__(self, parent, value):
        wx.Dialog.__init__(self, parent=parent,
            title="Edit list", size=self.DIALOG_SIZE)

        self.value = value

        vbox = wx.BoxSizer(wx.VERTICAL)
        stline = wx.StaticText(self, 11, "TEST DIALOG")
        vbox.Add(stline, 1, wx.ALIGN_CENTER | wx.TOP, 45)
        sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        vbox.Add(sizer, 0, wx.ALIGN_CENTER)
        self.SetSizer(vbox)

        self.Bind(wx.EVT_CLOSE, self.OnCancel)
        self.Bind(wx.EVT_BUTTON, self.OnOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=wx.ID_CANCEL)

    def OnOk(self, event):
        self.EndModal(wx.OK)

    def OnCancel(self, event):
        self.EndModal(wx.CANCEL)

    def GetValue(self):
        return self.value


class ListPropertyValue(object):
    """Contain list of properties such as styles, groups..."""
    def __init__(self, value, tag=None, attributes=None):
        """Try to copy value is value is object of this class
        
        @param value: list or ListPropertyValue
        @param tag: string, name of listed elements
        @param attributes: dictionary of attributes of listed elements
        
        @note: 2 ways to use
            1) ListPropertyValue(value), if value is ListPropertyValue instance
            2) ListPropertyValue([], tag, attr)
            
            if you will try ListPropertyValue([]) it will raise Exception, 
            because of tag and attr must be filled
            
        """
        if value.__class__ is self.__class__:
            self.properties = value.properties
            self.tag = value.tag
            self.attributes = value.attributes
        else:
            if not tag or not attributes:
                raise Exception("tag and attributes must be specified")
            self.properties = value
            self.tag = tag
            self.attributes = attributes


class ListProperty(wxpg.PyLongStringProperty):
    """Property for property grid that represents list of dictionaries"""

    def __init__(self, value, prop_grid, label, name=wxpg.LABEL_AS_NAME):
        wxpg.PyLongStringProperty.__init__(self, label, name)
        self.SetValue(value)
        self.prop_grid = prop_grid

    def GetClassName(self):
        return self.__class__.__name__

    def GetValueAsString(self, flags):
        """Just return property name + _list"""
        return "(%s_list)" % self.GetValue().tag

    def StringToValue(self, s, flags):
        """String to List is not valid conversion"""
        return False

    def OnButtonClick(self, prop_grid, value):
        #copy value and pass it to dialog
        _dlg = ListPropertyDialog(None, ListPropertyValue(self.GetValue()))
        if _dlg.ShowModal() == wx.OK:
            self.SetValue(_dlg.GetValue())
            self.prop_grid.fire_property_update(self)
        _dlg.Destroy()
        return True
