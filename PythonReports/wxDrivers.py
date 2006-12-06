"""Rendering utilities for wxPython backend"""
"""History (most recent first):
05-dec-2006 [als]   sweep pylint warnings
01-nov-2006 [als]   created
"""
__version__ = "$Revision: 1.2 $"[11:-2]
__date__ = "$Date: 2006/12/06 17:05:46 $"[7:-2]

__all__ = ["ImageDriver", "TextDriver"]

from cStringIO import StringIO
import os

import wx

from PythonReports import drivers

class ImageDriver(drivers.ImageDriver):

    """Image processing driver

    Instances of this driver class are created for each
    distinct image source, i.e. image file or data block.

    Instantiation must be done by one of the factory
    methods .fromfile() and .fromdata().

    """

    backend = "wx"

    _image = None   # wxImage object (not for external access)

    # we are not using wx.BITMAP_TYPE_ANY to verify that the type
    # passed to a factory method is accurate (unlike PIL, wx does
    # not report actual file format).
    TYPE_FLAGS = {
        "bmp": wx.BITMAP_TYPE_BMP,
        "gif": wx.BITMAP_TYPE_GIF,
        "jpg": wx.BITMAP_TYPE_JPEG,
        "jpeg": wx.BITMAP_TYPE_JPEG,
        "png": wx.BITMAP_TYPE_PNG,
        "pcx": wx.BITMAP_TYPE_PCX,
        "pnm": wx.BITMAP_TYPE_PNM,
        "tif": wx.BITMAP_TYPE_TIF,
        "tiff": wx.BITMAP_TYPE_TIF,
        "xpm": wx.BITMAP_TYPE_XPM,
        "ico": wx.BITMAP_TYPE_ICO,
        "cur": wx.BITMAP_TYPE_CUR,
        "ani": wx.BITMAP_TYPE_ANI,
    }

    @classmethod
    def _get_type_flag(cls, img_type):
        """Return wxImage construction flag for given image type"""
        try:
            return cls.TYPE_FLAGS[img_type]
        except KeyError:
            raise ValueError("Unsupported image type: %r" % img_type)

    @classmethod
    def fromfile(cls, filepath, img_type):
        """Create an image source from existing file

        Parameters:
            filepath: full path to the image file
            img_type: image type, e.g. "jpeg" or "png"

        Return value: new image wrapper object.

        """
        _rv = cls()
        _rv.filepath = filepath
        _rv.img_type = img_type
        _rv._image = wx.Image(filepath, cls._get_type_flag(img_type))
        return _rv

    @classmethod
    def fromdata(cls, data, img_type, name=None):
        """Create an image source from data block

        Parameters:
            data: image data
            img_type: image type, e.g. "jpeg" or "png"
            name: optional name of a report block containing data

        Return value: new image wrapper object.

        """
        _rv = cls()
        _rv.name = name
        _rv.img_type = img_type
        #_rv._image = wx.ImageFromStream(wx.InputStream(StringIO(data)),
        #    cls._get_type_flag(img_type))
        _rv._image = wx.ImageFromStream(StringIO(data),
            cls._get_type_flag(img_type))
        return _rv

    def getsize(self):
        """Return image size

        Return value: 2-element tuple (width, height).

        """
        return (self._image.GetWidth(), self._image.GetHeight())

    def _get_image_data(self, image, img_type=None):
        """Return image data as string

        Parameters:
            image: wx.Image object
            img_type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        This is a helper method for all methods returning image data.

        """
        if not img_type:
            # pylint: disable-msg=C0103
            # C0103: Invalid name "img_type"
            img_type = self.preferred_type
        # XXX shoud use a MemoryFileSystem to avoid creating a temporary file.
        _filename = os.tempnam(None, "primg")
        image.SaveFile(_filename, self._get_type_flag(img_type))
        _file = open(_filename, "rb")
        _rv = _file.read()
        _file.close()
        os.remove(_filename)
        return _rv

    def getdata(self, img_type=None):
        """Return image data as string

        Parameters:
            img_type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.

        """
        return self._get_image_data(self._image, img_type)

    def scale(self, width, height, img_type=None):
        """Return a scaled image

        Parameters:
            width: target image width
            height: target image height
            img_type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.

        """
        return self._get_image_data(self._image.Scale(width, height), img_type)

    def _cut(self, width, height, img_type):
        """Return an image cut to dimensions

        Parameters:
            width: target image width
            height: target image height
            img_type: image type, e.g. "jpeg" or "gif"

        Return value: image data as string.

        Each of target dimensions must be smaller or equal
        to current image size.  If either width or height
        passed is greater than current one, the effect is
        undefined.

        """
        _img = self._image.Size((width, height), (0, 0))
        return self._get_image_data(_img, img_type)

class TextDriver(drivers.TextDriver):

    """Text processing driver

    The driver is instantiated once for each report font
    and handles all texts printed out with that font.

    """

    backend = "wx"

    # wxPython has no API for getting any font metrics...
    # 1/5 of character size is default line gap used by ReportLab.
    DEFAULT_LEADING = .2

    def __init__(self, font):
        """Create text driver instance

        Parameters:
            font: report font definition (element instance)

        """
        super(TextDriver, self).__init__(font)
        self.font = font
        self.height = font.get("size")
        self.leading = int(self.height * self.DEFAULT_LEADING)
        self._dc = wx.MemoryDC()
        self._dc.SetFont(self._get_font(font))

    @staticmethod
    def _get_font(font):
        """Return wx.Font for given template/printout font element"""
        _attrs = {
            #"encoding": wx.FONTENCODING_UTF8,
            "family": wx.DECORATIVE,
            "faceName": font.get("typeface"),
            "pointSize": font.get("size"),
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
            if font.get(_prop, False):
                _attrs[_attr] = _value
        return wx.Font(**_attrs)

    def getsize(self, text):
        """Return size tuple (width, height) for given text"""
        return self._dc.GetTextExtent(text)

# vim: set et sts=4 sw=4 :
