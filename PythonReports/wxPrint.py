"""wxPython print classes

Warning: this module is malfunctional.  Print preview is badly broken
due to wxDC limitations.  Printer output may be broken too.

"""
"""History (most recent first):
20-oct-2006 [als]   Barcode X dimension attr renamed to "module"
20-oct-2006 [als]   added command-line application
03-oct-2006 [als]   support images
26-sep-2006 [als]   printout.Text does not use bgcolor
22-sep-2006 [als]   added bar code drawing (not functional yet)
06-sep-2006 [als]   disable text wrapping (must be properly wrapped in .prp);
                    remove -1 offset at bottom right corner of line boxes
30-aug-2006 [als]   ported from previous implementation
"""
__version__ = "$Revision: 1.1 $"[11:-2]
__date__ = "$Date: 2006/11/01 11:06:14 $"[7:-2]

from cStringIO import StringIO
import re
import sys

import wx

from PythonReports.datatypes import *
from PythonReports import printout as prp

class Printout(wx.Printout):

    def __init__(self, report, title=None):
        """Initialize printout

        Parameters:
            report: PRP file name or ElementTree with loaded report printout
            title: optional window title

        """
        if isinstance(report, basestring):
            if title is None:
                title = report
            report = prp.load(report)
        elif title is None:
            title = "Report Printout"
        super(Printout, self).__init__(title=title)
        self.report = report
        self.pages = report.findall("page")
        # element handlers
        self.handlers = {
            "line": self.DrawLine,
            "rectangle": self.DrawRectangle,
            "image": self.DrawImage,
            "text": self.DrawText,
            "barcode": self.DrawBarcode,
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
        self.imgdata = dict([(_element.get("name"), Data.get_data(_element))
            for _element in report.findall("data")])

    def GetPageInfo(self):
        _numpages = len(self.pages)
        return (1, _numpages, 1, _numpages)

    def HasPage(self, pageno):
        return (1 <= pageno <= len(self.pages))

    def GetColor(self, color):
        """Return wx.Color object for color value of an element attribute"""
        if color:
            return wx.Colour(*Color(color).rgb)
        else:
            return wx.NullColour

    def SetPen(self, type, color):
        """Change the pen of the DC

        Parameters:
            type: value returned by PenType.fromValue()
                (PenType or Dimension instance)
            color: pen color (Color instance)

        """
        _width = 1
        if type == "dot":
            _style = wx.DOT
        elif type == "dash":
            _style = wx.SHORT_DASH
        elif type == "dashdot":
            _style = wx.DOT_DASH
        else:
            _style = wx.SOLID
            _width = int(type)
        if _width:
            _pen = wx.Pen(self.GetColor(color), _width, _style)
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
            _brush = wx.Brush(self.GetColor(color))
        return _brush

    def OnPrintPage(self, pageno):
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

    def DrawLine(self, line):
        self.SetPen(line.get("pen"), line.get("color"))
        _box = Box.from_element(line.find("box"))
        _dc = self.GetDC()
        if line.get("backslant"):
            _dc.DrawLine(_box.right, _box.top, _box.left, _box.bottom)
        else:
            _dc.DrawLine(_box.left, _box.top, _box.right, _box.bottom)

    def DrawRectangle(self, rect):
        _box = Box.from_element(rect.find("box"))
        _radius = rect.get("radius")
        _dc = self.GetDC()
        _dc.SetBrush(self.GetBrush(rect.get("color")))
        self.SetPen(rect.get("pen"), rect.get("pencolor"))
        if _radius:
            _dc.DrawRoundedRectangle(_box.x, _box.y, _box.width, _box.height,
                _radius)
        else:
            _dc.DrawRectangle(_box.x, _box.y, _box.width, _box.height)

    def DrawImage(self, image):
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
                _data = Data.get_data(_data)
            _img = wx.ImageFromStream(wx.InputStream(StringIO(_data)))
        _box = Box.from_element(image.find("box"))
        if image.get("scale"):
            _img.Rescale(_box.width, _box.height)
        else:
            _img.Resize((_box.width, _box.height), (0, 0))
        self.GetDC().DrawBitmap(wx.BitmapFromImage(_img), _box.x, _box.y)

    _word_re = re.compile("\s*\S+\s*")
    def WrapLines(self, text, width):
        # allow the text to be 1 point wider (round error?)
        width += 1
        # if the text is not wider than required, return early
        _dc = self.GetDC()
        (_w, _h) = _dc.GetTextExtent(text)
        if _w <= width:
            return text
        # split text to words.  inter-word spaces go to previous word.
        _lines = []
        _words = self._word_re.findall(text)
        while _words:
            # scan backwards while the line is too wide
            _ii = len(_words)
            while _ii > 1:
                _line = "".join(_words[:_ii]).rstrip()
                (_w, _h) = _dc.GetTextExtent(_line)
                if _w <= width:
                    break
                _ii -= 1
            else:
                _line = _words[0].rstrip()
            # move found line from _words to _lines
            _lines.append(_line)
            _words = _words[_ii:]
        return "\n".join(_lines)

    def DrawText(self, text):
        _content = text.find("data").text
        if not _content:
            return
        _dc = self.GetDC()
        _dc.SetFont(self.fonts[text.get("font")])
        _dc.SetTextForeground(self.GetColor(text.get("color")))
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

    def DrawBarcode(self, barcode):
        _stripes = [int(_stripe)
            for _stripe in barcode.get("stripes").split(",")]
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
        if barcode.get("vertical"):
            _cur_y = _box.y
            for (_idx, _stripe) in enumerate(_stripes):
                if _idx & 1:
                    _dc.DrawRectangle(_box.x, _cur_y, _box.width, _stripe)
                _cur_y += _stripe
        else:
            _cur_x = _box.x
            for (_idx, _stripe) in enumerate(_stripes):
                if _idx & 1:
                    _dc.DrawRectangle(_cur_x, _box.y, _stripe, _box.height)
                _cur_x += _stripe
        # restore DC scale
        _dc.SetUserScale(_dc_scale_x, _dc_scale_y)

class Preview(wx.PrintPreview):

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

    def __init__(self, prp, *args, **kwargs):
        """Intialize the application

        Parameters:
            prp: name of the printout file
            remaining arguments are passed to the base class.

        """
        self.prp = prp
        super(PrintApp, self).__init__(*args, **kwargs)

    def OnInit(self):
        _preview = Preview(self.prp)
        if not _preview.Ok():
            raise RuntimeError, "Cannot initialize preview"
            return False
        _frame = wx.PreviewFrame(_preview, None, self.prp, size=(800, 600))
        _frame.Initialize()
        _frame.Show(True)
        return True

def run(argv=sys.argv):
    if len(argv) != 2:
        print "Usage: %s <printout>" % argv[0]
        sys.exit(2)
    _app = PrintApp(argv[1], 0)
    _app.MainLoop()

if __name__ == "__main__":
    run()

# vim: set et sts=4 sw=4 :
