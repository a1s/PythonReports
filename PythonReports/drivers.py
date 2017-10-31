"""PythonReports rendering utilities

This module contains base classes for text and image rendering drivers
and exports API function `get_driver`, used to get a driver implementation.

"""

__all__ = ["PIXEL", "get_driver"]

import re

# 1x1 transparent png image
PIXEL = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00' \
        '\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rI' \
        'DATx\xdac````\x00\x00\x00\x05\x00\x01z\xa8WP\x00\x00\x00\x00' \
        'IEND\xaeB`\x82'

_image_drivers = {}
_text_drivers = {}

def get_driver(driver_type, backend=None):
    """Return a rendering driver

    Parameters:
        driver_type: "Text" or "Image"
        backend: optional name of preferred backend,
            like "PIL" or "wx".  If omitted or None,
            use system preference.

    """
    if driver_type == "Text":
        _drivers = _text_drivers
    elif driver_type == "Image":
        _drivers = _image_drivers
    else:
        raise ValueError("Invalid driver type: %r" % driver_type)
    # if this is the first call for selected driver type,
    # load all available drivers
    if not _drivers:
        if driver_type == "Image":
            # Use ImageDriver class from this module as dummy fallback driver
            # (will be overwritten as soon as any actual driver is found).
            # This will raise NotImplementdedError when the first image
            # operation is attempted, but if there are no images in report
            # then we can get through without image driver.
            _driver = _image_drivers[None] = ImageDriver
            # most preferred backend goes last
            _backends = ("wx", "PIL")
        else:
            _driver = None
            _backends = ("Tk", "wx", "PIL", "RL")
        # NOTE backend preference:
        #   RL (ReportLab) is best for texts, no image support
        #   PIL is best for images (ReportLab image handling uses PIL too)
        #   wx can handle both but has serious drawbacks
        #   Tk has no image support, does not need 3rd party modules
        for _backend in _backends:
            _vars = {}
            try:
                # pylint: disable-msg=W0122
                # W0122: Use of the exec statement
                exec("from PythonReports.%sDrivers import %sDriver as Driver"
                    % (_backend, driver_type), _vars)
            except ImportError:
                continue
            else:
                _driver = _vars["Driver"]
                _drivers[_backend] = _driver
        if _driver is None:
            raise RuntimeError("No %s driver found" % driver_type)
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
    img_type = None # image type, e.g. "jpeg" or "png"
    use_count = 0   # number of references to this source, set/read by builder

    @property
    def preferred_type(self):
        """Return preferred image type

        If original image was jpeg (lossy encoding), return jpeg.
        Otherwise return png (preferred lossless storage format).

        """
        if self.img_type.lower() in ("jpeg", "jpg"):
            return "jpeg"
        else:
            return "png"

    @classmethod
    def fromfile(cls, filepath, img_type):
        """Create an image source from existing file

        Parameters:
            filepath: full path to the image file
            img_type: image type, e.g. "jpeg" or "png"

        Return value: new image wrapper object.

        """
        raise NotImplementedError

    @classmethod
    def fromdata(cls, data, img_type, name=None):
        """Create an image source from data block

        Parameters:
            data: image data
            img_type: image type, e.g. "jpeg" or "png"
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

    def getdata(self, img_type=None):
        """Return image data as string

        Parameters:
            img_type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.

        """
        raise NotImplementedError

    def scale(self, width, height, img_type=None):
        """Return a scaled image

        Parameters:
            width: target image width
            height: target image height
            img_type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.

        """
        raise NotImplementedError

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
        raise NotImplementedError

    def cut(self, width, height, img_type=None):
        """Return an image cut to dimensions

        Parameters:
            width: target image width
            height: target image height
            img_type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.
            Returned image may be smaller than requested size.

        Note: if the image is smaller than given size,
        .cut() does not add padding in order to keep
        existing background instead of adding a border
        of arbitrary selected color (and some image types
        do not support transparency).

        """
        if not img_type:
            # pylint: disable-msg=C0103
            # C0103: Invalid name "img_type"
            img_type = self.preferred_type
        (_my_width, _my_height) = self.getsize()
        return self._cut(min(width, _my_width), min(height, _my_height),
            img_type)

    def resize(self, width, height, scale=False, img_type=None):
        """Return resized image

        Parameters:
            width: target image width
            height: target image height
            scale: if False (default), the image is cut to given size.
                If True, the image is scaled to the size.
            img_type: optional image type, e.g. "jpeg" or "gif".
                Default: preferred output type (jpeg or png).

        Return value: image data as string.
            Returned image may be smaller than requested size.

        """
        if not img_type:
            # pylint: disable-msg=C0103
            # C0103: Invalid name "img_type"
            img_type = self.preferred_type
        (_my_width, _my_height) = self.getsize()
        if (width == _my_width) and (height == _my_height):
            # own size is ok
            _rv = self.getdata()
        elif scale:
            # may adjust to any size
            _rv = self.scale(width, height, img_type=img_type)
        elif (width > _my_width) or (height > _my_height):
            _rv = self.cut(width, height, img_type=img_type)
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
    leading = None  # distance between rows, in points

    def __init__(self, font):
        """Create text driver instance

        Parameters:
            font: report font definition (element instance)

        """
        # pylint: disable-msg=W0613
        # W0613: Unused argument 'font'
        super(TextDriver, self).__init__()

    def getsize(self, text):
        """Return size tuple (width, height) for given text"""
        raise NotImplementedError

    def _find_first_line(self, words, width):
        """Find longest starting sequence of words fitting into width

        This is private inner routine for L{wrap},
        called with increasingly aggressive splitting patterns.

        If a fitting sequence can be found, return pair
        (text_line, number_of_words_consumed).  If even
        the first word is not short enough, return (None, None)

        """
        # scan backwards while the line is too wide
        _ii = len(words)
        while _ii >= 1:
            _line = "".join(words[:_ii]).rstrip()
            _tw = self.getsize(_line)[0]
            if _tw <= width:
                return (_line, _ii)
            _ii -= 1
        return (None, None)

    # Note: not using "word character" matchers (e.g. \w)
    # because punctuation characters must be kept along
    # with words unless separated by blank space.
    _word_re = re.compile("\s*\S+\s*")
    _word_re_ends = re.compile(".*?[])},.:;!?]")
    def wrap(self, text, width):
        """Wrap the text to given width

        Parameters:
            text:
                string to wrap (unicode)
            width:
                required text width in points

        Return value: wrapped text (unicode)

        """
        _tw = self.getsize(text)[0]
        if _tw <= width:
            return text
        # split text to words.  inter-word spaces go to previous word.
        _lines = []
        # Normally, split by spaces
        _words = self._word_re.findall(text)
        while _words:
            (_line, _ii) = self._find_first_line(_words, width)
            if _ii is not None:
                _words = _words[_ii:]
            else:
                # Fit not found, try to find punctuation in the first word
                _word = _words[0].rstrip()
                if not _word:
                    del _words[0]
                    continue
                _chunks = self._word_re_ends.findall(_word)
                if _chunks:
                    (_line, _ii) = self._find_first_line(_chunks, width)
                if _ii is None:
                    # Try separate characters,
                    # convert leading blanks to single space
                    if _word[0].isspace():
                        _lines.append("")
                        _word = _word.lstrip()
                    (_line, _ii) = self._find_first_line(list(_word), width)
                if _ii is None:
                    # Even one character is too much; further we can't go
                    _line = _word[:1]
                # pop it out of the first word
                _words[0] = _word[len(_line):]
            _lines.append(_line)
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
        Returned height may be less than or greater than passed height.

        """
        # pylint: disable-msg=W0613
        # W0613: Unused argument 'height'
        if width > 0:
            return self.getsize(self.wrap(text, width))
        else:
            return self.getsize(text)

# vim: set et sts=4 sw=4 :
