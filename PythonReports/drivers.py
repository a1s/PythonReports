"""PythonReports rendering utilities

This module contains base classes for text and image rendering drivers
and exports API function `get_driver`, used to get a driver implementation.

"""
"""History (most recent first):
01-nov-2006 [als]   driver classes have backend name property
11-oct-2006 [als]   fix variable name in ImageDriver.resize
05-oct-2006 [als]   created
"""

__version__ = "$Revision: 1.2 $"[11:-2]
__date__ = "$Date: 2006/11/01 17:37:56 $"[7:-2]

__all__ = ["PIXEL", "get_driver"]

import re

# 1x1 transparent png image
PIXEL = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00' \
        '\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rI' \
        'DATx\xdac````\x00\x00\x00\x05\x00\x01z\xa8WP\x00\x00\x00\x00' \
        'IEND\xaeB`\x82'

_image_drivers = {}
_text_drivers = {}

def get_driver(type, backend=None):
    """Return a rendering driver

    Parameters:
        type: "Text" or "Image"
        backend: optional name of preferred backend,
            like "PIL" or "wx".  If omitted or None,
            use system preference.

    """
    if type == "Text":
        _drivers = _text_drivers
    elif type == "Image":
        _drivers = _image_drivers
    else:
        raise ValueError("Invalid driver type: %r" % type)
    # if this is the first call for selected driver type,
    # load all available drivers
    if not _drivers:
        _driver = None
        # NOTE backend preference:
        #   RL (ReportLab) is best for texts
        #   PIL is best for images (ReportLab image handling uses PIL too)
        #   wx can handle both, but with serious drawbacks.
        for _backend in ("wx", "PIL", "RL"): # most preferred last
            _vars = {}
            try:
                exec("from PythonReports.%sDrivers import %sDriver as Driver"
                    % (_backend, type), _vars)
            except ImportError:
                continue
            else:
                _driver = _vars["Driver"]
                _drivers[_backend] = _driver
        if _driver is None:
            raise RuntimeError("No %s driver found" % type)
        # last loaded driver is used by default
        _drivers[None] = _driver
    try:
        return _drivers[backend]
    except KeyError:
        # TODO: issue warning
        return _drivers[None]

### base classes for backend drivers

class ImageDriver(object):

    """Image processing driver

    Instances of this driver class are created for each
    distinct image source, i.e. image file or data block.

    Instantiation must be done by one of the factory
    methods .fromfile() and .fromdata().

    """

    backend = None  # backend name, must be set in child classes
    filepath = None # set when loaded from disk file
    name = None     # name of data block
    type = None     # image type, e.g. "jpeg" or "png"
    use_count = 0   # number of references to this source, set/read by builder

    @property
    def preferred_type(self):
        """Return preferred image type

        If original image was jpeg (lossy encoding), return jpeg.
        Otherwise return png (preferred lossless storage format).

        """
        if self.type.lower() in ("jpeg", "jpg"):
            return "jpeg"
        else:
            return "png"

    @classmethod
    def fromfile(cls, filepath, type):
        """Create an image source from existing file

        Parameters:
            filepath: full path to the image file
            type: image type, e.g. "jpeg" or "png"

        Return value: new image wrapper object.

        """
        raise NotImplementedError

    @classmethod
    def fromdata(cls, data, type, name=None):
        """Create an image source from data block

        Parameters:
            data: image data
            type: image type, e.g. "jpeg" or "png"
            name: optional name of a report block containing data

        Return value: new image wrapper object.

        """
        raise NotImplementedError

    @classmethod
    def nullimage(cls):
        """Return an image set to 1x1 transparent bitmap"""
        return cls.fromdata(PIXEL)

    def getsize(self):
        """Return image size

        Return value: 2-element tuple (width, height).

        """
        raise NotImplementedError

    def getdata(self, type=None):
        """Return image data as string

        Parameters:
            type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.

        """
        raise NotImplementedError

    def scale(self, width, height, type=None):
        """Return a scaled image

        Parameters:
            width: target image width
            height: target image height
            type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.

        """
        raise NotImplementedError

    def _cut(self, width, height, type):
        """Return an image cut to dimensions

        Parameters:
            width: target image width
            height: target image height
            type: image type, e.g. "jpeg" or "gif"

        Return value: image data as string.

        Each of target dimensions must be smaller or equal
        to current image size.  If either width or height
        passed is greater than current one, the effect is
        undefined.

        """
        raise NotImplementedError

    def cut(self, width, height, type=None):
        """Return an image cut to dimensions

        Parameters:
            width: target image width
            height: target image height
            type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.
            Returned image may be smaller than requested size.

        Note: if the image is smaller than given size,
        .cut() does not add padding in order to keep
        existing background instead of adding a border
        of arbitrary selected color (and some image types
        do not support transparency).

        """
        if not type:
            type = self.preferred_type
        (_my_width, _my_height) = self._image.size
        return self._cut(min(width, _my_width), min(height, _my_height), type)

    def resize(self, width, height, scale=False, type=None):
        """Return resized image

        Parameters:
            width: target image width
            height: target image height
            scale: if False (default), the image is cut to given size.
                If True, the image is scaled to the size.
            type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.
            Returned image may be smaller than requested size.

        """
        if not type:
            type = self.preferred_type
        (_my_width, _my_height) = self.getsize()
        if (width == _my_width) and (height == _my_height):
            # own size is ok
            _rv = self.getdata()
        elif scale:
            # may adjust to any size
            _rv = self.scale(width, height, type=type)
        elif (width > _my_width) or (heigth > _my_height):
            _rv = self.cut(width, height, type=type)
        else:
            # should cut, but the image is smaller than cut frame
            _rv = self.getdata()
        return _rv

class TextDriver(object):

    """Text processing driver

    The driver is instantiated once for each report font
    and handles all texts printed out with that font.

    """

    backend = None  # backend name, must be set in child classes
    height = None   # line height, in points
    leading = None  # distance between baselines of two subsequent rows,
                    # in points

    def __init__(self, font):
        """Create text driver instance

        Parameters:
            font: report font definition (element instance)

        """
        super(TextDriver, self).__init__()

    def getsize(self, text):
        """Return size tuple (width, height) for given text"""
        raise NotImplementedError

    # Note: not using "word character" matchers (e.g. \w)
    # because punctuation characters must be kept along
    # with words unless separated by blank space.
    _word_re = re.compile("\s*\S+\s*")
    def wrap(self, text, width):
        """Wrap the text to given width

        Parameters:
            text:
                string to wrap (unicode)
            width:
                required text width in points

        Return value: wrapped text (unicode)

        """
        (_w, _h) = self.getsize(text)
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
                (_w, _h) = self.getsize(_line)
                if _w <= width:
                    break
                _ii -= 1
            else:
                _line = _words[0].rstrip()
            # move found line from _words to _lines
            _lines.append(_line)
            _words = _words[_ii:]
        return "\n".join(_lines)

    def chop(self, text, height):
        """Chop the last lines of text to fit in given height

        Parameters:
            text:
                initial string (unicode)
            height:
                target text height (points)

        Return value: chopped text (unicode)

        """
        _numlines = int((height + self.leading) / (self.height + self.leading))
        return "\n".join(text.split("\n")[:_numlines])

    def stretch(self, text, width, height):
        """Return new dimensions for text bounding box

        Parameters:
            text:
                initial string (unicode)
            width, height:
                initial text dimensions (points)

        Return value: 2-element tuple (width, height).
        Returned width is less than or equal to passed width.
        Returned height may by less than or greater than passed height.

        """
        if width > 0:
            text = self.wrap(text, width)
        return self.getsize(text)

# vim: set et sts=4 sw=4 :
