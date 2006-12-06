"""Rendering utilities for Python Imaging Library (PIL) backend"""
"""History (most recent first):
05-dec-2006 [als]   sweep pylint warnings
01-nov-2006 [als]   driver classes have backend name property
05-oct-2006 [als]   use base classes for the rendering drivers
02-oct-2006 [als]   ImageDriver: added .nullimage()
29-sep-2006 [als]   added ImageDriver
26-sep-2006 [als]   TextDriver.getsize: adjust width by heuristic coefficient
26-sep-2006 [als]   font file resolving moved to the fonts module
04-sep-2006 [als]   TextDriver made stateful (font-based);
                    added TextDriver.getsize();
                    added TTF_NAMEs for Times New Roman and Courier New fonts
29-aug-2006 [als]   TextDriver ported from previous implementation
"""
__version__ = "$Revision: 1.3 $"[11:-2]
__date__ = "$Date: 2006/12/06 16:52:18 $"[7:-2]

__all__ = ["ImageDriver", "TextDriver"]

from cStringIO import StringIO

from PIL import Image, ImageFont

from PythonReports import drivers, fonts

class ImageDriver(drivers.ImageDriver):

    """Image processing driver

    Instances of this driver class are created for each
    distinct image source, i.e. image file or data block.

    Instantiation must be done by one of the factory
    methods .fromfile() and .fromdata().

    """

    backend = "PIL"

    _image = None   # PIL image object (not for external access)

    @property
    def img_type(self):
        """image type, e.g. "jpeg" or "png"

        This is "compute once" property,
        setting object type from image content.

        """
        _rv = self._image.format.lower()
        self.__dict__["img_type"] = _rv
        return _rv

    # Note: img_type argument is not used by object factories in PIL driver.

    @classmethod
    def fromfile(cls, filepath, img_type):
        """Create an image source from existing file

        Parameters:
            filepath: full path to the image file
            img_type: image type, e.g. "jpeg" or "png"
                (Note: not used by PIL driver.)

        Return value: new image wrapper object.

        """
        # pylint: disable-msg=W0613
        # W0613: Unused argument 'img_type' - the type is guessed from contents
        _rv = cls()
        _rv.filepath = filepath
        _rv._image = Image.open(filepath)
        return _rv

    @classmethod
    def fromdata(cls, data, img_type, name=None):
        """Create an image source from data block

        Parameters:
            data: image data
            img_type: image type, e.g. "jpeg" or "png"
                (Note: not used by PIL driver.)
            name: optional name of a report block containing data

        Return value: new image wrapper object.

        """
        # pylint: disable-msg=W0613
        # W0613: Unused argument 'img_type' - the type is guessed from contents
        _rv = cls()
        _rv.name = name
        _rv._image = Image.open(StringIO(data))
        return _rv

    def getsize(self):
        """Return image size

        Return value: 2-element tuple (width, height).

        """
        return self._image.size

    def getdata(self, img_type=None):
        """Return image data as string

        Parameters:
            img_type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.

        """
        if not img_type:
            # pylint: disable-msg=C0103
            # C0103: Invalid name "img_type"
            img_type = self.preferred_type
        _buffer = StringIO()
        self._image.save(_buffer, format=img_type)
        return _buffer.getvalue()

    def scale(self, width, height, img_type=None):
        """Return a scaled image

        Parameters:
            width: target image width
            height: target image height
            img_type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.

        """
        if not img_type:
            # pylint: disable-msg=C0103
            # C0103: Invalid name "img_type"
            img_type = self.preferred_type
        _img = self._image.resize((width, height), Image.ANTIALIAS)
        _buffer = StringIO()
        _img.save(_buffer, format=img_type)
        return _buffer.getvalue()

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
        _img = self._image.crop((0, 0, width, height))
        _buffer = StringIO()
        _img.save(_buffer, format=img_type)
        return _buffer.getvalue()

class TextDriver(drivers.TextDriver):

    """Text processing driver

    The driver is instantiated once for each report font
    and handles all texts printed out with that font.

    """

    backend = "PIL"

    # PIL does not report the leading.
    # 1/5 of character size is default line gap used by ReportLab.
    DEFAULT_LEADING = .2

    def __init__(self, font):
        """Create text driver instance

        Parameters:
            font: report font definition (element instance)

        """
        super(TextDriver, self).__init__(font)
        _fontfile = fonts.fontfile(*[font.get(_attr)
            for _attr in ("typeface", "bold", "italic")])
        self.font = ImageFont.truetype(_fontfile, font.get("size"))
        self.height = sum(self.font.getmetrics())
        self.leading = int(self.height * self.DEFAULT_LEADING)

    def getsize(self, text):
        """Return size tuple (width, height) for given text"""
        # ImageFont.getsize() works for single-line texts only;
        # second member of returned tuple always is character height
        if "\n" in text:
            # have to aggregate dimensions manually
            _lines = text.split("\n")
            _height = (self.height + self.leading) * len(_lines) - self.leading
            _width = max([self.font.getsize(_line)[0] for _line in _lines])
        else:
            # single line - that's easy!
            (_width, _height) = self.font.getsize(text)
        # heuristics: width returned by PIL is about 1.1 times smaller...
        return (_width * 1.12, _height)

# vim: set et sts=4 sw=4 :
