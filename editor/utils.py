"""Additional tools for editor"""
"""
30-mar-2012 [kacah]   created

"""
import PythonReports.datatypes as datatypes
import wx

PT_TO_PIX = 0

def setup():
    """Get screen PDI and setup conversion from points to pixels factor"""
    global PT_TO_PIX

    _DPI = wx.ScreenDC().GetPPI()[0]

    _in_to_pt = datatypes.Dimension("1in")
    PT_TO_PIX = _DPI / _in_to_pt

def dim_to_screen(dimension):
    """Convert PythonReports dimension into screen pixels"""
    return round(dimension * PT_TO_PIX)

def get_or_create_by_id(elements_list, id, creation_function):
    """Get element with given id, or return result of creation function"""

    for _element in elements_list:
        if _element.id == id:
            return _element

    return creation_function(id)

def destroy_difference(old_list, new_list):
    """Destroy objects that contain old list and don't contain new"""

    from sets import Set
    _old = Set(old_list)
    _new = Set(new_list)
    _diff = _old - _new

    for _obj in _diff:
        _obj.destroy()
