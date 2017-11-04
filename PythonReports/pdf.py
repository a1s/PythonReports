#! /usr/bin/env python
"""PDF output for PythonReports"""

__all__ = ["PdfWriter", "write"]

import os
import sys

from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics, ttfonts
from reportlab.pdfgen import canvas

# reportlab requires PIL for images.  so do we.
# XXX is it possible to put jpeg images without PIL?
try:
    from PIL import Image
except ImportError:
    # images will be disabled
    Image = None

from PythonReports.datatypes import *
from PythonReports import fonts, printout as prp

class PdfWriter(object):

    """PDF renderer for PythonReports Printout (PRP) files"""

    # color values
    WHITE = (1.0, 1.0, 1.0)
    BLACK = (0.0, 0.0, 0.0)

    # pdf output canvas - will be created in .write()
    canvas = None
    # canvas state properties
    pagesize = (595, 842) # A4
    strokecolor = BLACK
    fillcolor = BLACK
    pen = 1 # datatypes.Pen value
    # textobject state properties
    textobject = None
    font = None
    wordspace = 0

    def __init__(self, report):
        """Initialize the writer

        Parameters:
            report: PRP file name or ElementTree with loaded report printout

        """
        super(PdfWriter, self).__init__()
        if isinstance(report, basestring):
            self.report = prp.load(report)
        else:
            self.report = report
        # element handlers
        self.handlers = {
            "line": self.drawLine,
            "rectangle": self.drawRectangle,
            "text": self.drawText,
            "barcode": self.drawBarcode,
            "outline": self.addOutline,
        }
        if Image:
            # PIL is loaded - can process images
            self.handlers["image"] = self.drawImage
            _images = {}
            for _element in self.report.findall("data"):
                _data = StringIO(prp.Data.get_data(_element))
                # data blocks may be used for other purposes too.
                # if PIL says it's not an image, skip it.
                try:
                    _img = Image.open(_data)
                except IOError:
                    continue
                else:
                    _images[_element.get("name")] = _img
            self.named_images = _images
        _fonts = {}
        _registered = set()
        _rlfonts = {}
        for (_name, _font) in self.report.fonts.iteritems():
            _typeface = _font.get("typeface")
            _bold = _font.get("bold")
            _italic = _font.get("italic")
            _size = _font.get("size")
            _facename = _typeface
            if _bold:
                _facename += " Bold"
            if _italic:
                _facename += " Italic"
            if _facename not in _registered:
                _fontfile = fonts.fontfile(_typeface, _bold, _italic)
                _font = ttfonts.TTFont(_facename, _fontfile)
                # XXX ReportLab cannot handle different fonts
                # with same internal typeface name.
                _rlname = _font.face.name + _font.face.subfontNameX
                if _rlname in _rlfonts:
                    # TODO: warning
                    _facename = _rlfonts[_rlname]
                else:
                    pdfmetrics.registerFont(_font)
                    _rlfonts[_rlname] = _facename
                _registered.add(_facename)
            # leading is 120% of the font size
            _fonts[_name] = (_facename, _size, _size * 1.2)
        self.fonts = _fonts

    def write(self, filepath=None, compression=True, encrypt=None):
        """Write the report to PDF file

        Parameters:
            filepath: output filepath.
            compression: if False, turn off compression of the PDF
                operations stream for each page.  Compressed documents
                will be smaller, but slower to generate.
            encrypt: password string
                or reportlab.lib.pdfencrypt.StandardEncryption object
                used to protect the document contents.

        """
        self.canvas = canvas.Canvas(filepath, pageCompression=compression,
            pagesize=self.pagesize, encrypt=encrypt)
        for _page in self.report.findall("page"):
            # PDF does not keep colors and pen size from previous page.
            # Make sure we have proper values.
            self.strokecolor = self.fillcolor = self.pen = None
            self.setPageSize(_page.get("width"), _page.get("height"))
            # draw elements
            for _item in _page:
                # if current item is not a text
                # and there is accumulated text, write it down
                if (_item.tag != "text") and self.textobject:
                    self._flushText()
                try:
                    _handler = self.handlers[_item.tag]
                except KeyError:
                    # no handler for element type - ignore element
                    continue
                _handler(_item)
            # output accumulated text, if any
            if self.textobject:
                self._flushText()
            # finalize page output
            self.canvas.showPage()
        self.canvas.save()

    def _flushText(self):
        """output current text object and discard it"""
        self.canvas.drawText(self.textobject)
        self.textobject = None
        self.font = None

    # stateful canvas proxies
    # the canvas output PDF code at once for each state change operation
    # following methods keep current settings and suppress code output
    # when the state is not changed

    def setPageSize(self, width, height):
        """Set paper size for this and subsequent pages

        Parameters:
            width: page width in points
            height: page height in points

        """
        if self.pagesize != (width, height):
            self.canvas.setPageSize((width, height))
            self.pagesize = (width, height)

    def setStrokeColor(self, color):
        """Set the stroke color

        Parameters:
            color: datatypes.Color object or None

        Return True if the color is set (not None),
        False otherwise.

        """
        if color is None:
            return False
        _rgb = color.rgbf
        if self.strokecolor != _rgb:
            self.canvas.setStrokeColorRGB(*_rgb)
            self.strokecolor = _rgb
        return True

    def setFillColor(self, color):
        """Set the stroke color

        Parameters:
            color: datatypes.Color object or None

        Return True if the color is set (not None),
        False otherwise.

        """
        if color is None:
            return False
        _rgb = color.rgbf
        if self.fillcolor != _rgb:
            self.canvas.setFillColorRGB(*_rgb)
            self.fillcolor = _rgb
        return True

    def setPen(self, pen):
        """Change stroke style and width

        Parameters:
            pen: datatypes.Pen object or None

        Return True if the pen is opaque (not None
        and not zero-width), False otherwise.

        """
        if pen is None:
            return False
        if pen == self.pen:
            return True
        if self.pen in ("dot", "dash", "dashdot"):
            _width = 1
            _solid = False
        else:
            _width = self.pen
            _solid = True
        _newwidth = 1
        if pen == "dot":
            self.canvas.setDash((1, 3))
        elif pen == "dash":
            self.canvas.setDash((3,))
        elif pen == "dashdot":
            self.canvas.setDash((3, 1, 1, 1))
        else:
            _newwidth = pen
        if _newwidth == 0:
            return False
        if not ((pen in ("dot", "dash", "dashdot")) or _solid):
            # switch from dashed to solid
            self.canvas.setDash(())
        if _width != _newwidth:
            self.canvas.setLineWidth(_newwidth)
        self.pen = pen
        return True

    def setWordSpace(self, wordspace=0):
        """Set word spacing

        Parameters:
            space: additional space to add between words.

        Note: PDF adds wordspace is to *each* character
        with code <20> (ASCII space character).

        """
        if wordspace != self.wordspace:
            self.textobject.setWordSpace(wordspace)
            self.wordspace = wordspace

    # drawing

    def getDimensions(self, element):
        """Return position and size of the element box

        Parameters:
            element: one of printout elements.
                Must have a "box" child element.

        Return value: 4-element tuple (x, y, width, height)
        where (x, y) is position of the upper left corner.

        """
        _box = element.find("box")
        _height = _box.get("height")
        return (_box.get("x"), self.pagesize[1] - _box.get("y") - _height,
            _box.get("width"), _height)

    def addOutline(self, element):
        """Add a document outline entry"""
        _key = element.get("name")
        self.canvas.bookmarkPage(_key, "FitH", left=element.get("x", 0),
            top=(self.pagesize[1] - element.get("y", 0)))
        self.canvas.addOutlineEntry(element.get("title"),
            _key, element.get("level", 1) - 1, element.get("closed"))

    def drawLine(self, line):
        """Draw a line"""
        # set line style, return if the line is not visible
        if not (self.setStrokeColor(line.get("color"))
            and self.setPen(line.get("pen"))
        ):
            return
        # get coordinates
        (_x1, _y1, _width, _height) = self.getDimensions(line)
        _x2 = _x1 + _width
        if line.get("backslant"):
            _y2 = _y1
            _y1 = _y2 + _height
        else:
            _y2 = _y1 + _height
        # draw
        self.canvas.line(_x1, _y1, _x2, _y2)

    def drawRectangle(self, rect):
        """Draw a rectangle"""
        _stroke = self.setStrokeColor(rect.get("pencolor")) \
            and self.setPen(rect.get("pen"))
        _fill = self.setFillColor(rect.get("color"))
        _radius = rect.get("radius")
        if _radius:
            self.canvas.roundRect(
                *(self.getDimensions(rect) + (_radius, _stroke, _fill)))
        else:
            self.canvas.rect(*(self.getDimensions(rect) + (_stroke, _fill)))

    def drawImage(self, image):
        """Draw an image"""
        _scale = image.get("scale", True)
        # actually, builder embeds all images into the printout
        if image.find("data") is not None:
            _data = StringIO(prp.Data.get_data(image.find("data")))
            _img = Image.open(_data)
        elif image.get("data"):
            _img = self.named_images[image.get("data")]
        else:
            _img = image.get("file")
            # it is better to use filename unless we have to cut the image
            # (scale will be done by reportlab)
            if not _scale:
                _img = Image.open(_img)
        (_x, _y, _width, _height) = self.getDimensions(image)
        if _scale:
            self.canvas.drawImage(ImageReader(_img), _x, _y, _width, _height)
        else:
            (_img_width, _img_height) = _img.size
            _img = _img.crop((0, 0, int(min(_width, _img_width)),
                int(min(_height, _img_height))))
            self.canvas.drawImage(ImageReader(_img), _x, _y)

    def drawText(self, text):
        """Draw a text block"""
        _content = text.find("data").text
        if not _content:
            return
        # convert all newline sequences into '\n'
        _content = _content.replace("\r\n", "\n") \
            .replace("\n\r", "\n").replace("\r", "\n")

        _align = text.get("align")
        # if there is no active text object, make one
        if not self.textobject:
            self.textobject = self.canvas.beginText()
        _tobj = self.textobject
        # update font
        _font = text.get("font")
        (_fontname, _fontsize, _leading) = self.fonts[_font]
        if _font != self.font:
            _tobj.setFont(_fontname, _fontsize, _leading)
            self.font = _font
        _color = text.get("color").rgbf
        if _color != self.fillcolor:
            _tobj.setFillColorRGB(*_color)
            self.fillcolor = _color
        # set starting point
        (_x, _y, _width, _height) = self.getDimensions(text)
        # text origin is baseline of the first line.
        # go to the top of the box and then down to the baseline.
        _ascent = pdfmetrics.getAscent(_fontname) / 1000. * _fontsize
        _y += _height - _ascent
        # vertical size of the box should be as close
        # to the text height as the builder can get.
        # center the text (ascent) vertically in the box.
        _y -= (_height - _leading * _content.count("\n") - _ascent) / 2
        _tobj.setTextOrigin(_x, _y)
        # reset word spacing unless we do justified text
        if _align != "justified":
            self.setWordSpace(0)
        # draw lines
        _offset = 0
        for _line in _content.split("\n"):
            if _align != "left":
                _pad = _width - pdfmetrics.stringWidth(_line,
                    _fontname, _fontsize)
            if _align == "right":
                _tobj.moveCursor(_pad - _offset, 0)
                _offset = _pad
            elif _align == "center":
                _tobj.moveCursor((_pad / 2.0) - _offset, 0)
                _offset = _pad / 2.0
            elif _align == "justified":
                self.setWordSpace(_pad / _line.count(" "))
            _tobj.textLine(_line)

    def drawBarcode(self, barcode):
        """Draw Bar Code symbol"""
        _xdim = barcode.get("module") / 1000. * 72.
        _stripes = [[int(_stripe) * _xdim for _stripe in _row.split(",")]
            for _row in barcode.get("stripes").split(" ")]
        # blank out the symbol area
        _canvas = self.canvas
        (_x, _y, _width, _height) = self.getDimensions(barcode)
        self.setFillColor(Color("white"))
        _canvas.rect(_x, _y, _width, _height, False, True)
        # Although we set stroke=False on black elements, they come out
        # slightly wider than blanks, especially on low-DPI printers.
        # Make the bars slightly reduced to avoid that.
        _downsize_black = 0.05
        # draw bars
        self.setFillColor(Color("black"))
        if len(_stripes) > 1: # 2D barcode
            _cur_y = _y + _height
            for _row in _stripes:
                _cur_x = _x
                for (_idx, _stripe) in enumerate(_row):
                    if _idx & 1:
                        _canvas.rect(_cur_x, _cur_y,
                            _stripe - _downsize_black,
                            _xdim - _downsize_black,
                            stroke=False, fill=True)
                    _cur_x += _stripe
                _cur_y -= _xdim
        elif barcode.get("vertical"):
            _cur_y = _y + _height
            for (_idx, _stripe) in enumerate(_stripes[0]):
                if _idx & 1:
                    _canvas.rect(_x, _cur_y, _width,
                        _stripe - _downsize_black,
                        stroke=False, fill=True)
                _cur_y -= _stripe
        else:
            _cur_x = _x
            for (_idx, _stripe) in enumerate(_stripes[0]):
                if _idx & 1:
                    _canvas.rect(_cur_x, _y,
                        _stripe - _downsize_black, _height,
                        stroke=False, fill=True)
                _cur_x += _stripe

def write(report, filepath, compression=True, encrypt=None):
    """Create PDF document from PythonReports printout

    Parameters:
        report: PRP file name or ElementTree with loaded report printout
        filepath: output file path.
        compression: if False, turn off compression of the PDF
            operations stream for each page.  Compressed documents
            will be smaller, but slower to generate.
        encrypt: password string
            or reportlab.lib.pdfencrypt.StandardEncryption object
            used to protect the document contents.

    """
    PdfWriter(report).write(filepath, compression, encrypt)

def run(argv=sys.argv):
    """Command line executable"""
    if len(argv) not in (2, 3):
        print "Usage: %s <printout> [<pdf>]" % argv[0]
        sys.exit(2)
    _printout = argv[1]
    if len(argv) > 2:
        _pdf = argv[2]
    else:
        _pdf = os.path.splitext(_printout)[0] + ".pdf"
    write(_printout, _pdf)

if __name__ == "__main__":
    run()

# vim: set et sts=4 sw=4 :
