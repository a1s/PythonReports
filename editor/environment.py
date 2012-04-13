"""Contain global application objects and data. Link objects."""
"""
04-apr-2012 [kacah]    created

"""
workspace = None
properties_grid = None
file_toolbar = None
visual_toolbar = None
shell = None

last_focus = None

class EditingTools(object):
    """Enumeration for supported tools in elements editing"""

    select = 1
    field = 2
    line = 3
    rect = 4
    image = 5
    barcode = 6

def setup_environment(worksp, prop_grid, sh, file_tool, visual_tool):
    """Set global windows and objects"""

    global workspace
    global properties_grid
    global file_toolbar
    global visual_toolbar
    global shell

    workspace = worksp
    properties_grid = prop_grid
    shell = sh
    file_toolbar = file_tool
    visual_toolbar = visual_tool

def OnPropertyListener(listener):
    """Unfocus last element, focus new, update properties in properties grid"""

    remove_focus()
    #try to highlight new element
    try:
        listener.highlight(True)
    except:
        pass

    properties_grid.setup_by_element(listener)

    global last_focus
    last_focus = listener

def remove_focus():
    """Set focus to None, and clear property grid"""

    global last_focus

    #try to unhighlight last element
    #try cause of last_focus may be None or may not have highlight method
    try:
        last_focus.highlight(False)
    except:
        pass

    properties_grid.unsetup()

    last_focus = None

def get_active_editing_tool():
    """Return active edit tool - selected from toolbar"""

    return visual_toolbar.get_selected_tool()

def toggle_double_buffering(enabled):
    """Enable or disable double buffering for workspace. 
    
    Needed to fix ogl bug in double buffered containers
    
    """
    workspace.SetDoubleBuffered(enabled)

def get_predefined_data(data_name):
    """Get data element from current report element. 
    
    @return Data element or None if report or data not found
    
    """
    _report = workspace.get_report()
    if not _report:
        return None

    _data_list = _report.get_value("lists", "data").get_all()
    for _data in _data_list:
        if _data.get_value("data", "name") == data_name:
            return _data

    return None
