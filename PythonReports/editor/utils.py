"""Additional tools for editor"""

import os
import sys

import wx

import PythonReports.datatypes as datatypes
import PythonReports.editor.pyrres as pyrres

PT_TO_PIX = 0

def setup():
    """Initialize editor environment

    Get screen PDI and setup conversion from points to pixels factor.

    Add current directory to the module path.

    """
    global PT_TO_PIX
    _DPI = wx.ScreenDC().GetPPI()[0]
    _in_to_pt = datatypes.Dimension("1in")
    PT_TO_PIX = _DPI / _in_to_pt

    if "." not in sys.path:
        sys.path.insert(0, ".")

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

def get_resource_dir():
    return os.path.join(os.path.dirname(__file__), "res")

def get_resource_img(imgname):
    return getattr(pyrres, imgname).GetImage()

def get_resource_ico(iconame):
    return getattr(pyrres, iconame).GetIcon()

def get_icon(icon_name):
    """Get icon as bitmap by given filename

    @raise Exception: if not found or unknown file format

    """
    return get_resource_img(icon_name).ConvertToBitmap()

# vim: set et sts=4 sw=4 :
