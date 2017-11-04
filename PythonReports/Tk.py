#! /usr/bin/env python
"""Tk output for PythonReports"""

__all__ = []

import base64
import sys
from Tkinter import *

from PythonReports.datatypes import *
from PythonReports import drivers, fonts, printout as prp

def dimension(points):
    """Return Tk dimension for given number of points"""
    if not points:
        return 0
    else:
        return "%.2fp" % points

class Painter(object):

    """Draw PRP pages on Tk canvas"""

    def __init__(self, report):
        """Initialize the painter

        Parameters:
            report: PRP file name or ElementTree with loaded report printout

        """
        super(Painter, self).__init__()
        if isinstance(report, basestring):
            self.report = prp.load(report)
        else:
            self.report = report
        self.pages = self.report.findall("page")
        # element handlers
        self.handlers = {
            "line": self.drawLine,
            "rectangle": self.drawRectangle,
            "text": self.drawText,
            "barcode": self.drawBarcode,
        }
        try:
            self.image_driver = drivers.get_driver("Image")
        except KeyError:
            # no image driver found
            self.image_driver = None
        else:
            # can process images
            self.handlers["image"] = self.drawImage
            self.named_images = {}
        _fonts = {}
        for (_name, _font) in self.report.fonts.iteritems():
            _modifiers = []
            if _font.get("bold"):
                _modifiers.append("bold")
            if _font.get("italic"):
                _modifiers.append("italic")
            _fonts[_name] = (_font.get("typeface"), _font.get("size"),
                " ".join(_modifiers))
        self.fonts = _fonts
        self.scaled_fonts = _fonts
        self.scale = 1.0

    def pagecount(self):
        """Return number of pages in the printout"""
        return len(self.pages)

    def pagesize(self, pageno):
        """Return (width, height) tuple for given page number

        Parameters:
            pageno: integer page number (zero-based).

        Return value: 2-element tuple (width, height) containing
            page dimensions in points.

        """
        _page = self.pages[pageno]
        return (_page.get("width"), _page.get("height"))

    def paint(self, canvas, pageno, scale=1.0):
        """Draw single printout page on Tk canvas

        Parameters:
            canvas: Tkinter Canvas object
            pageno: integer page number (zero-based)
            scale: optional scaling factor (default: 1.0)

        """
        _page = self.pages[pageno]
        # images are automatically deleted when they go out of scope
        # (i.e. immediately after an image is drawn).
        # to make images visible, we attach a list of the image objects
        # to the canvas.
        canvas.printout_images = []
        # set the scale and compute scaled font sizes
        if scale < .1:
            # zoom to less than 10% is disallowed
            self.scale = .1
        else:
            self.scale = scale
        self.scaled_fonts = dict([
            (_name, (_face, max(1, int(round(_size * self.scale))), _options))
            for (_name, (_face, _size, _options)) in self.fonts.iteritems()])
        # draw elements
        for _item in _page:
            try:
                _handler = self.handlers[_item.tag]
            except KeyError:
                # no handler for element type - ignore element
                pass
            else:
                _handler(canvas, _item)

    @staticmethod
    def _lineattrs(pen):
        """Return a line attribute dictionary for given pen type

        Parameters:
            pen: object created by datatypes.Pen

        Return value: a dictionary with "width" and "stipple"
            options set according to pen type.

        """
        _rv = {}
        if pen == "dot":
            _rv["dash"] = ". "
        elif pen == "dash":
            _rv["dash"] = "- "
        elif pen == "dashdot":
            _rv["dash"] = "- . "
        elif pen == 0:
            _rv["width"] = 0
        else:
            _rv["width"] = dimension(pen)
        return _rv

    def getDimensions(self, element):
        """Return position and size of the element box

        Parameters:
            element: one of printout elements.
                Must have a "box" child element.

        Return value: 4-element tuple (x0, y0, x1, y1).

        """
        _box = Box.from_element(element.find("box"))
        return tuple(dimension(_dim * self.scale)
            for _dim in (_box.left, _box.top, _box.right, _box.bottom))

    def drawLine(self, canvas, line):
        """Draw a line"""
        (_x0, _y0, _x1, _y1) = self.getDimensions(line)
        if not line.get("backslant"):
            (_y0, _y1) = (_y1, _y0)
        canvas.create_line(_x0, _y0, _x1, _y1, fill=str(line.get("color")),
            **self._lineattrs(line.get("pen")))

    def drawRectangle(self, canvas, rect):
        """Draw a rectangle"""
        _options = {"outline": str(rect.get("pencolor"))}
        _options.update(self._lineattrs(rect.get("pen")))
        _color = rect.get("color")
        if _color:
            _options["fill"] = str(_color)
        canvas.create_rectangle(*self.getDimensions(rect), **_options)

    def _get_named_image(self, name, img_type):
        """Return an image loaded from a named data element"""
        # pylint: disable-msg=W0631,W0704
        # W0631: Using possibly undefined loop variable '_element' -
        #   if the loop didn't run, raise error before the variable is used
        # W0704: Except doesn't do anything - if the image was
        #   not loaded yet, it will be handled after try/except block.
        try:
            return self.named_images[(name, img_type)]
        except KeyError:
            pass
        for _element in self.report.findall("data"):
            if _element.get("name") == name:
                break
        else:
            raise KeyError("data element with name=%r cannot be found" % name)
        _img = self.image_driver.fromdata(Data.get_data(_element), img_type)
        self.named_images[(name, img_type)] = _img
        return _img

    def drawImage(self, canvas, image):
        """Draw an image"""
        _type = image.get("type")
        _img = image.get("file")
        if _img:
            _img = self.image_driver.fromfile(_img, _type)
        else:
            _img = image.get("data")
            if _img:
                _img = self._get_named_image(_img, _type)
            else:
                # image data must be child element
                _img = self.image_driver.fromdata(
                    Data.get_data(image.find("data")), _type)
        _box = image.find("box")
        _width = canvas.winfo_pixels(dimension(_box.get("width") * self.scale))
        _height = canvas.winfo_pixels(
            dimension(_box.get("height") * self.scale))
        # data for PhotoImage must be base64-encoded gif
        _data = _img.resize(_width, _height, image.get("scale"),
            img_type="gif")
        _img = PhotoImage(data=base64.b64encode(_data))
        canvas.printout_images.append(_img)
        canvas.create_image(anchor=NW, image=_img,
            *self.getDimensions(image)[:2])

    def drawText(self, canvas, text):
        """Draw a text block"""
        _content = text.find("data").text
        if not _content:
            return
        _options = {
            "text": _content,
            "font": self.scaled_fonts[text.get("font")],
            "fill": str(text.get("color")),
        }
        if "\n" in _content:
            # pylint: disable-msg=W0704
            # W0704: Except doesn't do anything - if justify code is unknown,
            #   we just ignore it (resulting in left-justified text).
            # can use Tk text justify
            try:
                _options["justify"] = {
                    "right": RIGHT, "center": CENTER}[text.get("align")]
            except KeyError:
                # left justify (default) or fill (unsupported)
                pass
            canvas.create_text(anchor=NW,
                *self.getDimensions(text)[:2], **_options)
        else:
            # one-line text - must adjust the anchor for requested alignment
            _align = text.get("align")
            _box = Box.from_element(text.find("box"))
            _box.rescale(self.scale)
            if _align == "right":
                _options["anchor"] = NE
                _x = _box.right
            elif _align == "center":
                _options["anchor"] = N
                _x = _box.left + (_box.width / 2)
            else:
                _options["anchor"] = NW
                _x = _box.left
            canvas.create_text(dimension(_x), dimension(_box.top), **_options)

    def drawBarcode(self, canvas, barcode):
        """Draw Bar Code symbol"""
        _xdim = barcode.get("module") / 1000. * 72.
        _stripes = [[int(_stripe) * _xdim for _stripe in _row.split(",")]
            for _row in barcode.get("stripes").split(" ")]
        # blank out the symbol area
        _box = Box.from_element(barcode.find("box"))
        _box.rescale(self.scale)
        canvas.create_rectangle(fill="white", width=0,
            *map(dimension, (_box.left, _box.top, _box.right, _box.bottom)))
        # draw bars
        if len(_stripes) > 1: # 2D barcode
            _cur_y = _box.y
            for _row in _stripes:
                _cur_x = _box.x
                _next_y = _cur_y + _xdim
                for (_idx, _stripe) in enumerate(_row):
                    _next_x = _cur_x + _stripe
                    if _idx & 1:
                        canvas.create_rectangle(fill="black", width=0,
                            *map(dimension,
                                (_cur_x, _cur_y, _next_x, _next_y)))
                    _cur_x = _next_x
                _cur_y = _next_y
        elif barcode.get("vertical"):
            _cur_y = _box.y
            for (_idx, _stripe) in enumerate(_stripes[0]):
                if _idx & 1:
                    canvas.create_rectangle(fill="black", width=0,
                        *map(dimension,
                            (_box.x, _cur_y, _box.right, _cur_y + _stripe)))
                _cur_y += _stripe
        else:
            _cur_x = _box.x
            for (_idx, _stripe) in enumerate(_stripes[0]):
                if _idx & 1:
                    canvas.create_rectangle(fill="black", width=0,
                        *map(dimension,
                            (_cur_x, _box.y, _cur_x + _stripe, _box.bottom)))
                _cur_x += _stripe

class PreviewWidget(Frame):

    """Printout display widget"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - from base class

    PAGE_PADDING = 10 # padding around the page on the preview canvas

    # toolbar images - created at first instantiation
    img_first = img_prev = img_next = img_last = img_magnifier = None

    def __init__(self, report, master, **options):
        """Initialize preview

        Parameters:
            report: PRP file name or ElementTree with loaded report printout
            master: parent window
            options: Tkinter Frame constructor options

        """
        Frame.__init__(self, master, class_="PythonReportsWidget", **options)
        if isinstance(report, basestring):
            self.report = prp.load(report)
        else:
            self.report = report
        self.painter = Painter(self.report)
        self.pageno = 1
        self.pagevar = StringVar()
        self.scale = 1.0
        self.zoomvar = StringVar()
        self.zoomvar.set("100%")
        # if button images were not created yet, make'em now
        if self.img_first is None:
            _cls = self.__class__
            _cls.img_first = PhotoImage(data="R0lGODlhCgANAIABADNmzP///yH5BA"
                "EKAAEALAAAAAAKAA0AAAIXBIIZdrrsmFFyomrx1Fkn/1WR5DxWVAAAOw==")
            _cls.img_prev = PhotoImage(data="R0lGODlhCgANAIABADNmzP///yH5BA"
                "EKAAEALAAAAAAIAA0AAAIUjB+ABortGDywyZqqzfhuv0xh9BQAOw==")
            _cls.img_next = PhotoImage(data="R0lGODlhCgANAIABADNmzP///yH5BA"
                "EKAAEALAAAAAAIAA0AAAIVRI4Blrq9HorS0UOj1ZvtxE3e1BwFADs=")
            _cls.img_last = PhotoImage(data="R0lGODlhCgANAIABADNmzP///yH5BA"
                "EKAAEALAAAAAAKAA0AAAIXRI4Ba6ncEFxp0mNvphtbOVWQM5KXWQAAOw==")
            _cls.img_magnifier = PhotoImage(data="R0lGODlhDQANAMIFAAAAAMzMzJ"
                "mZmQD//2ZmZv///////////yH5BAEKAAcALAAAAAANAA0AAAMueLoHDowBE"
                "oKAEYgxRCDYAgRDVYXKaJEB2lBk516UcGXT4z6R5PSiHzDlGhoPCQA7")
        # create the toolbar
        _toolbar = Frame(self)
        _toolbar.grid(row=0, column=0, columnspan=2, sticky=EW)
        self.button_first = Button(_toolbar, image=self.img_first,
            command=self.OnButtonFirst)
        self.button_prev = Button(_toolbar, image=self.img_prev,
            command=self.OnButtonPrev)
        _entry = Entry(_toolbar, textvariable=self.pagevar, width=3)
        self.button_next = Button(_toolbar, image=self.img_next,
            command=self.OnButtonNext)
        self.button_last = Button(_toolbar, image=self.img_last,
            command=self.OnButtonLast)
        self.button_first.pack(side=LEFT, ipadx=2, ipady=1)
        self.button_prev.pack(side=LEFT, ipadx=2, ipady=1)
        _entry.pack(side=LEFT, fill=Y, padx=2, pady=1)
        self.button_next.pack(side=LEFT, ipadx=2, ipady=1)
        self.button_last.pack(side=LEFT, ipadx=2, ipady=1)
        if self.painter.pagecount() > 1:
            _entry.bind("<FocusOut>", self.OnPageNumber)
            _entry.bind("<Return>", self.OnPageNumber)
        else:
            _entry["state"] = DISABLED
        Label(_toolbar, width=1).pack(side=LEFT)
        Label(_toolbar, image=self.img_magnifier).pack(side=LEFT,
            fill=Y, padx=2, ipady=2)
        _btncmd = self.register(self.OnZoomSpin)
        _entry = Spinbox(_toolbar, width=5, textvariable=self.zoomvar,
            command=(_btncmd, "%d"))
        _entry.bind("<FocusOut>", self.OnZoomEntry)
        _entry.bind("<Return>", self.OnZoomEntry)
        _entry.pack(side=LEFT, fill=Y, ipady=1)
        # bind button commands to key combinations too
        # XXX cannot get following bindings to work...
        #self.bind("<Control-Next>", self.OnButtonFirst)
        #self.bind("<Next>", self.OnButtonNext)
        #self.bind("<Prior>", self.OnButtonPrev)
        # create canvas with attached scrollbars
        _xscrollbar = Scrollbar(self, orient=HORIZONTAL)
        _xscrollbar.grid(row=2, column=0, sticky=EW)
        _yscrollbar = Scrollbar(self)
        _yscrollbar.grid(row=1, column=1, sticky=NS)
        _canvas = Canvas(self, bd=2, relief=SUNKEN,
            xscrollcommand=_xscrollbar.set, yscrollcommand=_yscrollbar.set)
        _canvas.grid(row=1, column=0, sticky=NSEW)
        _xscrollbar.config(command=_canvas.xview)
        _yscrollbar.config(command=_canvas.yview)
        self.canvas = _canvas
        _canvas.bind("<Button-3>", self.OnBeginDrag)
        _canvas.bind("<B3-Motion>", self.OnDrag)
        _canvas.bind("<ButtonRelease-3>", self.OnEndDrag)
        # make canvas cell grow in both dimensions
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.pack()
        # display the first page
        self.ShowPage(1)

    def ShowPage(self, pageno):
        """Display a page

        Parameters:
            pageno - page number

        """
        # make sure pageno is in range
        _pagecount = self.painter.pagecount()
        _pageno = pageno # don't update argument to make pylint happy
        if _pageno < 0:
            _pageno += _pagecount
        if _pageno > _pagecount:
            _pageno = _pagecount
        elif _pageno < 1:
            _pageno = 1
        # enable/disable navigation buttons
        if _pageno == 1:
            self.button_first["state"] = DISABLED
            self.button_prev["state"] = DISABLED
        elif self.pageno == 1:
            # previous state was DISABLED
            self.button_first["state"] = NORMAL
            self.button_prev["state"] = NORMAL
        if _pageno == _pagecount:
            self.button_next["state"] = DISABLED
            self.button_last["state"] = DISABLED
        elif self.pageno == _pagecount:
            self.button_next["state"] = NORMAL
            self.button_last["state"] = NORMAL
        # delete all objects from canvas
        _canvas = self.canvas
        _canvas.delete("ALL")
        # update canvas dimensions
        (_width, _height) = self.painter.pagesize(_pageno - 1)
        _width *= self.scale
        _height *= self.scale
        _canvas["scrollregion"] = tuple(map(dimension, (
            -self.PAGE_PADDING, -self.PAGE_PADDING,
            _width + self.PAGE_PADDING, _height + self.PAGE_PADDING)))
        # display the page
        _canvas.create_rectangle(0, 0, dimension(_width), dimension(_height),
            fill="white", width="1p")
        self.painter.paint(_canvas, _pageno - 1, self.scale)
        _canvas.addtag_all("ALL")
        # update state
        self.pageno = _pageno
        self.pagevar.set(str(_pageno))

    def OnButtonFirst(self):
        """Go to the first page"""
        self.ShowPage(1)

    def OnButtonPrev(self):
        """Go to previous page"""
        self.ShowPage(self.pageno - 1)

    def OnButtonNext(self):
        """Go to next page"""
        self.ShowPage(self.pageno + 1)

    def OnButtonLast(self):
        """Go to the last page"""
        self.ShowPage(self.painter.pagecount())

    def OnPageNumber(self, event):
        """Go to the specified page number"""
        _value = self.pagevar.get()
        event.widget.select_range(0, len(_value))
        self.ShowPage(int(_value))

    def OnBeginDrag(self, event):
        """Start dragging the image"""
        self.canvas["cursor"] = "fleur"
        self.canvas.scan_mark(event.x, event.y)

    def OnDrag(self, event):
        """Drag the preview image"""
        self.canvas.scan_dragto(event.x, event.y)

    def OnEndDrag(self, event):
        """End preview dragging"""
        self.canvas["cursor"] = ""

    def _get_zoom_value(self):
        """Return zoom value from spinbox entry.

        If entry value is not valid, return current zoom level.

        """
        # pylint: disable-msg=W0702
        # W0702: No exception's type specified
        #   i wonder what type of exception can occur here?
        _val = self.zoomvar.get().replace("%", "")
        try:
            return int(_val)
        except:
            return int(self.scale * 100)

    def OnZoomSpin(self, direction):
        """Change zoom level by 10% up or down"""
        _z10 = int(self._get_zoom_value() / 10)
        if direction == "up":
            _z10 += 1
        else:
            _z10 -= 1
        self.Zoom(_z10 * 10)

    def OnZoomEntry(self, event):
        """Zoom to entered value"""
        self.Zoom(self._get_zoom_value())

    def Zoom(self, percentage):
        """Zoom the page

        Parameters:
            percentage: zoom level, in percents.

        """
        if percentage < 10:
            # pylint: disable-msg=C0103
            # C0103: Invalid name "percentage"
            percentage = 10
        self.scale = percentage / 100.
        self.zoomvar.set("%i%%" % percentage)
        self.ShowPage(self.pageno)

class PreviewWindow(Toplevel):

    """Toplevel window displaying a printout"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - from base class

    def __init__(self, report, title=None, **options):
        """Create the window

        Parameters:
            report: PRP file name or ElementTree with loaded report printout
            title: optional window title
            options: Tkinter Toplevel widget constructor options

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
        Toplevel.__init__(self, class_="PythonReportsWindow", **options)
        self.title(title)
        _preview = PreviewWidget(report, self)
        _preview.pack(fill=BOTH, expand=1)

def run(argv=sys.argv):
    """Command line executable"""
    if len(argv) != 2:
        print "Usage: %s <printout>" % argv[0]
        sys.exit(2)
    _root = Tk()
    _root.withdraw()
    _win = PreviewWindow(argv[1])
    # XXX passing width and height to the constructor does not work.  why?
    _win.geometry("800x600")
    _root.wait_window(_win)

if __name__ == "__main__":
    run()

# vim: set et sts=4 sw=4 :
