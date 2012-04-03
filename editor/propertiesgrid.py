"""Elements for working with Property Grid"""
"""
02-apr-2012 [kacah]    Added property synchronization
29-mar-2012 [kacah]    Added Colors for None, REQUIRED properties
27-mar-2012 [kacah]    Added list properties dialog
26-mar-2012 [kacah]    Added list properties
23-mar-2012 [kacah]    Added empty properties
20-mar-2012 [kacah]    created

"""
import PythonReports.datatypes as datatypes
import wx
import wx.propgrid as wxpg

import datatypes_binding

class PropertiesListener(object):
    """Listen while control get or lost focus and update property grid"""

    def __init__(self, prop_grid=None):
        self.prop_grid = prop_grid

        #attributes and child validated elements
        self.properties = {}

    def OnSelected(self, evt=None, prop_grid=None):
        """Use this when your element is selected to force prop grid update
        
        @note: BIND this to one of the wx events (for example ON_FOCUS) or
            use this function directly. 
            
            If prop_grid is passed uses it, otherwise uses self.prop_grid.
            Throws Exception if both prop grids are None
        
        """
        if prop_grid:
            prop_grid.setup_by_element(self)
        elif self.prop_grid:
            self.prop_grid.setup_by_element(self)
        else:
            raise Exception("No property grid found")

    def OnUnselected(self, evt=None, prop_grid=None):
        """Clear prop grid after deselection. Same use as OnSelected"""

        if prop_grid:
            prop_grid.unsetup(self)
        elif self.prop_grid:
            self.prop_grid.unsetup(self)
        else:
            raise Exception("No property grid found")

    def after_property_changed(self, category, prop_name):
        """Do something after property was changed. 
        
        @param category: name of property's category
        @param prop_name: name of property  
        
        @note: Override this in child classes if necessary 
        
        """
        pass

    def update_property(self, changed_property):
        """Update property in dictionary by property grid's Property
        
        @note: Parent = category
        
        """
        _cat = changed_property.GetParent().GetName()
        _attr = changed_property.GetName()

        (_value, _type, _default_value) = self.properties[_cat][_attr]

        _conversion_function = \
            datatypes_binding.DATATYPES_SETTINGS[_type.__name__].conversion_func
        _value = _conversion_function(changed_property, _type)
        self.properties[_cat][_attr] = (_value, _type, _default_value)

        self.after_property_changed(_cat, _attr)

    def OnPropGridChange(self, event):
        """Change element state in parent"""

        _property = event.GetProperty()
        if _property:
            self.update_property(_property)

    def add_attr_ONE(self, tag, attributes):
        """Add attributes that always exist
        
        @param tag: category name
        @param attributes: tuple (ValueType, default_value/None/REQUIRED)
        
        """

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

        #create ONE category for ALL unrestricted properties
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

    def get_category(self, tag):
        """Return category by name"""
        try:
            return self.properties[tag]
        except:
            raise Exception("No category found - %s" % tag)

    def get_value(self, tag, attribute):
        """Return value of given category and attribute"""
        try:
            return self.properties[tag][attribute][0]
        except:
            raise Exception("No property found - %s: %s" % (tag, attribute))

    def synchronize_attributes(self, tag, attributes):
        """Add values from another dictionary, do not create new attributes
        
        @param tag: category name
        @param attributes: dictionary of attributes, value is property tuple
        
        """
        #check if category exists
        try:
            self.get_category(tag)
        except:
            return

        for (_attr, _prop_tuple) in attributes.items():
            #check if value exists
            try:
                self.get_value(tag, _attr)
            except:
                continue
            (_value, _type, _default_value) = _prop_tuple
            (_value_old, _type_old, _default_old) = self.properties[tag][_attr]
            #check if types are similar and values not
            if _type is _type_old and _value != _value_old:
                self.properties[tag][_attr] = \
                    (_value, _type, _default_value)
                self.after_property_changed(tag, _attr)


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
                raise Exception("Property doesn't attached")


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

    NONE_COLOR = wx.Color(253, 159, 173)
    REQUIRED_COLOR = wx.Color(69, 186, 111)

    def set_property_color(self, prop, prop_type):
        """Set color of property, by given type (None, REQUIRED, else)"""

        _cell = prop.GetOrCreateCell(0)

        if prop_type is None:
            _cell.SetBgCol(self.NONE_COLOR)
        elif prop_type is datatypes.REQUIRED:
            _cell.SetBgCol(self.REQUIRED_COLOR)

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
        #client data = if this property can be unspecified
        _property.SetClientData(_default_value is None)
        self.set_property_color(_property, _default_value)

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

    DIALOG_SIZE = (600, 500)

    def __init__(self, parent, value):
        wx.Dialog.__init__(self, parent=parent,
            title="Edit list", size=self.DIALOG_SIZE)

        self.value = value

        _hbox = wx.BoxSizer(wx.HORIZONTAL)
        _hbox.Add(self.create_list_box(), 2, wx.EXPAND | wx.ALL, 5)
        _hbox.Add(self.create_control_bar(), 1, wx.EXPAND | wx.ALL, 5)
        _hbox.Add(self.create_property_bar(), 2, wx.EXPAND | wx.ALL, 5)

        _buttons_line = self.CreateButtonSizer(wx.OK)

        _vbox = wx.BoxSizer(wx.VERTICAL)
        _vbox.Add(_hbox, 1, wx.EXPAND | wx.TOP, 5)
        _vbox.Add(_buttons_line, 0, wx.ALIGN_CENTER | wx.ALL, 15)
        self.SetSizer(_vbox)

        self.update_list()

    def create_list_box(self):
        """Create list bar and return something to add to sizer"""

        _sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.prop_list = wx.ListBox(self, wx.ID_ANY)
        self.Bind(wx.EVT_LISTBOX, self.OnListItemSelect, self.prop_list)
        _sizer.Add(self.prop_list, 1, wx.EXPAND | wx.ALL, 5)
        return _sizer

    def create_control_bar(self):
        """Create buttons for adding, deleting and moving elements"""

        #buttons - (name, on_click_function, top_margin)
        BUTTONS = [
            ("Add", self.OnAddButton, 45),
            ("Remove", self.OnRemoveButton, 15),
            ("Up", self.OnUpButton, 15),
            ("Down", self.OnDownButton, 15),
        ]

        _button_box = wx.BoxSizer(wx.VERTICAL)
        for _params in BUTTONS:
            _button = wx.Button(self, wx.ID_ANY, _params[0])
            self.Bind(wx.EVT_BUTTON, _params[1], _button)
            _button_box.Add(_button, 0, wx.ALIGN_CENTER | wx.TOP, _params[2])

        return _button_box

    def create_property_bar(self):
        """Create property bar and return something to add to sizer"""

        _border = wx.StaticBox(self, label="Properties")
        _boxsizer = wx.StaticBoxSizer(_border, wx.HORIZONTAL)
        self.prop_grid = PropertiesGrid(self)
        _boxsizer.AddStretchSpacer(1)
        _boxsizer.Add(self.prop_grid, 20, wx.EXPAND | wx.ALL, 5)
        _boxsizer.AddStretchSpacer(1)
        return _boxsizer

    def update_list(self, selected_item=None):
        """Populate listbox with elements from value list"""

        _values = self.value.get_all()
        self.prop_list.Clear()
        self.prop_grid.unsetup()
        for _value in _values:
            self.prop_list.Append(_value.name)

        #try to get and restore selected value
        if selected_item:
            _index = self.value.find(selected_item)
            if _index > -1:
                self.prop_list.SetSelection(_index)
                selected_item.OnSelected(prop_grid=self.prop_grid)

    def OnListItemSelect(self, event):
        _index = event.GetSelection()
        self.value.get(_index).OnSelected(prop_grid=self.prop_grid)

    def OnAddButton(self, event):
        """Add new element into value and update list"""

        self.value.add()
        _list_elmt = None
        _index = self.prop_list.GetSelection()
        if _index >= 0:
            _list_elmt = self.value.get(_index)
        self.update_list(_list_elmt)

    def _run_if_selected(self, _run_func):
        """Run given function if item is selected and update list"""

        _index = self.prop_list.GetSelection()
        if _index >= 0:
            _elem = self.value.get(_index)
            _run_func(_index)
            self.update_list(_elem)

    def OnRemoveButton(self, event):
        self._run_if_selected(self.value.remove)

    def OnUpButton(self, event):
        self._run_if_selected(self.value.move_up)

    def OnDownButton(self, event):
        self._run_if_selected(self.value.move_down)

    def GetValue(self):
        return self.value


class ListPropertyValue(object):
    """Contain list of properties such as styles, groups..."""

    class ListElement(PropertiesListener):
        """Element in property list"""

        elem_id = 0

        def __init__(self, tag, attributes):
            """Use only one category - element self"""
            PropertiesListener.__init__(self)

            if attributes:
                self.add_attr_ONE(tag, attributes)

            self.id = self.generate_id()
            self.name = "%s %s" % (tag, self.id)

        @classmethod
        def generate_id(cls):
            """Generate unique name for this element. Good for recognizing it"""

            cls.elem_id += 1
            return cls.elem_id

    def __init__(self, values, tag, attributes):
        """New list property
            
        @param values: list of ListElements
        @param tag: string, name of listed elements
        @param attributes: dictionary of attributes of listed elements
        
        """
        self.values = values
        self.tag = tag
        self.attributes = attributes

    def has_element(self, index):
        """Check if there is a property with given index"""
        return index < len(self.values) and index >= 0

    def add(self):
        """Add new element to list"""
        _elmt = self.ListElement(self.tag, self.attributes)
        self.values.append(_elmt)
        return _elmt

    def get(self, index):
        """Get element by given index, None is not found"""
        if self.has_element(index):
            return self.values[index]
        else:
            return None

    def get_all(self):
        return self.values

    def get_by_id(self, id):
        """Get element by given id, None if not found"""

        for _elem in self.values:
            if _elem.id == id:
                return _elem

        return None

    def find(self, elem):
        """Get index of given element, return -1 if doesn't exist"""
        try:
            return self.values.index(elem)
        except:
            return -1

    def remove(self, index):
        """Remove element form list by given index"""
        if self.has_element(index):
            del self.values[index]
        else:
            raise Exception("Out of index")

    def move(self, from_index, to_index):
        """Move element form index to index."""
        self.values.insert(to_index, self.values.pop(from_index))

    def move_up(self, index):
        """Move element closer to list start"""
        if self.has_element(index):
            if index > 0:
                self.move(index, index - 1)
        else:
            raise Exception("Out of index")

    def move_down(self, index):
        """Move element closer to list end"""
        if self.has_element(index):
            if index < len(self.values) - 1:
                self.__move(index, index + 1)
        else:
            raise Exception("Out of index")


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
        _dlg = ListPropertyDialog(None, self.GetValue())
        _dlg.ShowModal()
        _dlg.Destroy()
        self.prop_grid.fire_property_update(self)
        return True
