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
    """Unfocus last element, update properties in properties grid"""

    global last_focus
    #try to unhighlight last element
    #try cause of last_focus may be None or may not have highlight method
    try:
        last_focus.highlight(False)
    except:
        pass
    #try to highlight new element
    try:
        listener.highlight(True)
    except:
        pass

    properties_grid.setup_by_element(listener)
    last_focus = listener
