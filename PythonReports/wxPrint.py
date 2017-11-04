#! /usr/bin/env python
"""wxPython print classes

Warning: this module is malfunctional.  Print preview is badly broken
due to wxDC limitations.  Printer output may be broken too.

"""

from cStringIO import StringIO
import re
import sys

import wx

from PythonReports.datatypes import *
from PythonReports import printout as prp

class Printout(wx.Printout):

    """wxWidgets printout document"""

    # pylint: disable-msg=R0904
    # R0904: Too many public methods - most come from the base class

    def __init__(self, report, title=None):
        """Initialize printout

        Parameters:
            report: PRP file name or ElementTree with loaded report printout
            title: optional window title

        """
        if isinstance(report, basestring):
            # pylint: disable-msg=C0103
            # C0103: Invalid names "report", "title"
            if title is None:
                title = report
            report = prp.load(report)
        elif title is None:
            # pylint: disable-msg=C0103
            # C0103: Invalid name "title"
            title = "Report Printout"
        super(Printout, self).__init__(title=title)
        self.report = report
        self.pages = report.findall("page")
        # element handlers
        self.handlers = {
            "line": self.drawLine,
            "rectangle": self.drawRectangle,
            "image": self.drawImage,
            "text": self.drawText,
            "barcode": self.drawBarcode,
        }
        _fonts = {}
        for (_name, _font) in report.fonts.iteritems():
            _attrs = {
                #"encoding": wx.FONTENCODING_UTF8,
                "family": wx.DECORATIVE,
                "faceName": _font.get("typeface"),
                "pointSize": _font.get("size"),
                "style": wx.NORMAL,
                "weight": wx.NORMAL,
            }
            # on windows, positive size is cell height
            # and negative size is character height
            if wx.Platform == "__WXMSW__":
                _attrs["pointSize"] = -_attrs["pointSize"]
            for (_prop, _attr, _value) in (
                ("bold", "weight", wx.BOLD),
                ("italic", "style", wx.ITALIC),
                ("underline", "underline", True),
            ):
                if _font.get(_prop, False):
                    _attrs[_attr] = _value
            _fonts[_name] = wx.Font(**_attrs)
        self.fonts = _fonts
        self.imgdata = dict([
            (_element.get("name"), prp.Data.get_data(_element))
            for _element in report.findall("data")])

    def GetPageInfo(self):
        """Return available page ranges"""
        _numpages = len(self.pages)
        return (1, _numpages, 1, _numpages)

    def HasPage(self, pageno):
        """Return True for existing page number"""
        return (1 <= pageno <= len(self.pages))

    @staticmethod
    def getColor(color):
        """Return wx.Color object for color value of an element attribute"""
        if color:
            return wx.Colour(*Color(color).rgb)
        else:
            return wx.NullColour

    def setPen(self, pen_type, color):
        """Change the pen of the DC

        Parameters:
            pen_type: value returned by PenType.fromValue()
                (PenType or Dimension instance)
            color: pen color (Color instance)

        """
        _width = 1
        if pen_type == "dot":
            _style = wx.DOT
        elif pen_type == "dash":
            _style = wx.SHORT_DASH
        elif pen_type == "dashdot":
            _style = wx.DOT_DASH
        else:
            _style = wx.SOLID
            _width = int(pen_type)
        if _width:
            _pen = wx.Pen(self.getColor(color), _width, _style)
        else:
            _pen = wx.TRANSPARENT_PEN
        self.GetDC().SetPen(_pen)

    def GetBrush(self, color):
        """Return drawing brush for given color

        Parameters:
            color: pen color (Color instance) or None.

        If color is None, the brush is set to transparent.
        Otherwise the brush is set to solid color fill.

        """
        if color is None:
            _brush = wx.Brush(wx.NullColour, wx.TRANSPARENT)
        else:
            _brush = wx.Brush(self.getColor(color))
        return _brush

    def OnPrintPage(self, pageno):
        """Draw selected page to the output device context"""
        try:
            _page = self.pages[pageno - 1]
        except IndexError:
            return False
        # set DC scaling
        _dc = self.GetDC()
        (_width, _height) = _dc.GetSizeTuple()
        _dc.SetUserScale(float(_width) / _page.get("width"),
            float(_height) / _page.get("height"))
        # draw elements
        for _item in _page:
            try:
                _handler = self.handlers[_item.tag]
            except KeyError:
                # no handler for element type - ignore element
                pass
            else:
                _handler(_item)
        return True

    def drawLine(self, line):
        """Draw a line"""
        self.setPen(line.get("pen"), line.get("color"))
        _box = Box.from_element(line.find("box"))
        _dc = self.GetDC()
        if line.get("backslant"):
            _dc.DrawLine(_box.right, _box.top, _box.left, _box.bottom)
        else:
            _dc.DrawLine(_box.left, _box.top, _box.right, _box.bottom)

    def drawRectangle(self, rect):
        """Draw a rectangle"""
        _box = Box.from_element(rect.find("box"))
        _radius = rect.get("radius")
        _dc = self.GetDC()
        _dc.SetBrush(self.GetBrush(rect.get("color")))
        self.setPen(rect.get("pen"), rect.get("pencolor"))
        if _radius:
            _dc.DrawRoundedRectangle(_box.x, _box.y, _box.width, _box.height,
                _radius)
        else:
            _dc.DrawRectangle(_box.x, _box.y, _box.width, _box.height)

    def drawImage(self, image):
        """Draw an image"""
        _file = image.get("file")
        if _file:
            _img = wx.Image(_file)
        else:
            _name = image.get("data")
            if _name:
                _data = self.imgdata[_name]
            else:
                # look for data sub-element
                _data = image.find("data")
                if _data is None:
                    # XXX raise an error?
                    return
                _data = prp.Data.get_data(_data)
            _img = wx.ImageFromStream(wx.InputStream(StringIO(_data)))
        _box = Box.from_element(image.find("box"))
        if image.get("scale"):
            _img.Rescale(_box.width, _box.height)
        else:
            _img.Resize((_box.width, _box.height), (0, 0))
        self.GetDC().DrawBitmap(wx.BitmapFromImage(_img), _box.x, _box.y)

    def drawText(self, text):
        """Draw a text block"""
        _content = text.find("data").text
        if not _content:
            return
        _dc = self.GetDC()
        _dc.SetFont(self.fonts[text.get("font")])
        _dc.SetTextForeground(self.getColor(text.get("color")))
        _align = text.get("align")
        if _align == "left":
            _alignment = wx.ALIGN_LEFT
        elif _align == "right":
            _alignment = wx.ALIGN_RIGHT
        else:
            # TODO: justify
            _alignment = wx.ALIGN_CENTER_HORIZONTAL
        _box = Box.from_element(text.find("box"))
        _dc.DrawLabel(_content, (_box.x, _box.y, _box.width, _box.height),
            _alignment)
        #if _strike:
        #    _dc.SetPen(wx.Pen(_color, 1, wx.SOLID))
        #    _x = _re.x + (_re.height / 2)
        #    _dc.DrawLine(_x, _re.y, _x, _re.y + _re.width - 1)

    def drawBarcode(self, barcode):
        """Draw Bar Code symbol"""
        _stripes = [[int(_stripe) for _stripe in _row.split(",")]
            for _row in barcode.get("stripes").split(" ")]
        # temporary set DC scale to X-dimension
        _scale = barcode.get("module") / 1000. * 72.
        # (Note: current DC scale is points)
        _dc = self.GetDC()
        (_dc_scale_x, _dc_scale_y) = _dc.GetUserScale()
        _dc.SetUserScale((_dc_scale_x / _scale), (_dc_scale_y / _scale))
        _box = Box.from_element(barcode.find("box"))
        _box.rescale(_scale)
        # blank the box
        _dc.SetBrush(wx.WHITE_BRUSH)
        _dc.SetPen(wx.TRANSPARENT_PEN)
        _dc.DrawRectangle(_box.x, _box.y, _box.width, _box.height)
        # draw bars
        _dc.SetBrush(wx.BLACK_BRUSH)
        if len(_stripes) > 1: # 2D barcode
            _cur_y = _box.y
            for _row in _stripes:
                _cur_x = _box.x
                for (_idx, _stripe) in enumerate(_row):
                    if _idx & 1:
                        _dc.DrawRectangle(_cur_x, _cur_y, _stripe, 1)
                    _cur_x += _stripe
                _cur_y += 1
        elif barcode.get("vertical"):
            _cur_y = _box.y
            for (_idx, _stripe) in enumerate(_stripes[0]):
                if _idx & 1:
                    _dc.DrawRectangle(_box.x, _cur_y, _box.width, _stripe)
                _cur_y += _stripe
        else:
            _cur_x = _box.x
            for (_idx, _stripe) in enumerate(_stripes[0]):
                if _idx & 1:
                    _dc.DrawRectangle(_cur_x, _box.y, _stripe, _box.height)
                _cur_x += _stripe
        # restore DC scale
        _dc.SetUserScale(_dc_scale_x, _dc_scale_y)

class Preview(wx.PrintPreview):

    """Print Preview manager"""

    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    def __init__(self, report, title=None, print_data=None):
        """Initialize print preview

        Parameters:
            report: PRP file name or ElementTree with loaded report printout
            title: optional window title
            print_data: optional wx.PrintData object

        """
        _view = Printout(report, title)
        _print = Printout(report, title)
        wx.PrintPreview.__init__(self, _view, _print, print_data)

class PrintApp(wx.App):

    """Simple application for preview and printing of a printout"""

    # pylint: disable-msg=R0901,R0904
    # R0901: Too many ancestors - sorry, cannot help it
    # R0904: Too many public methods - same as in the base class

    def __init__(self, printout, *args, **kwargs):
        """Intialize the application

        Parameters:
            printout: name of the printout file
            remaining arguments are passed to the base class.

        """
        self.prp = printout
        super(PrintApp, self).__init__(*args, **kwargs)

    def OnInit(self):
        """Start the application: create main frame and open report preview"""
        _preview = Preview(self.prp)
        if not _preview.Ok():
            raise RuntimeError, "Cannot initialize preview"
            # if raise is changed to MessageBox, return False here
        _frame = wx.PreviewFrame(_preview, None, self.prp, size=(800, 600))
        _frame.Initialize()
        _frame.Show(True)
        return True

def run(argv=sys.argv):
    """Command line executable"""
    if len(argv) != 2:
        print "Usage: %s <printout>" % argv[0]
        sys.exit(2)
    _app = PrintApp(argv[1], 0)
    _app.MainLoop()

if __name__ == "__main__":
    run()

# vim: set et sts=4 sw=4 :
