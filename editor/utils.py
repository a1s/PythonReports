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
