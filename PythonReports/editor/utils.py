"""Additional tools for editor"""
"""
26-may-2012 [als]   compute ICONS_DIR path from the module file path
30-mar-2012 [kacah] created
"""

import os

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
    return round(dimension * PT_TO_PIX * wx.GetApp().zoom_get())

def screen_to_dim(pix):
    """Convert screen pixels into PythonReports dimenson"""
    return datatypes.Dimension(pix / PT_TO_PIX / wx.GetApp().zoom_get())

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

def scale_bitmap(bitmap, width, height):
    """Scale given bitmap to a new dimensions"""

    if width < 1:
        width = 1
    if height < 1:
        height = 1

    _image = wx.ImageFromBitmap(bitmap)
    _image = _image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    return wx.BitmapFromImage(_image)

def rotate90_bitmap(bitmap, clockwise):
    """Rotate bitmap by 90 degrees on the given direction"""

    _image = wx.ImageFromBitmap(bitmap)
    _image = _image.Rotate90(clockwise)
    return wx.BitmapFromImage(_image)

ICONS_DIR = os.path.join(os.path.dirname(__file__), "res")

def get_icon(icon_name):
    """Get icon as bitmap by given filename

    @raise Exception: if not found or unknown file format

    """
    _file = os.path.join(ICONS_DIR, icon_name)
    return wx.Image(_file, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
