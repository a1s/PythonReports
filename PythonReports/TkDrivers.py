"""Rendering utilities for Tkinter backend

This module contains no image driver: Tkinter
does not provide sufficient image functionality.

"""
"""History (most recent first):
12-dec-2006 [als]   fix italic fonts: option name is "slant", not "style"
05-dec-2006 [als]   sweep pylint warnings
04-nov-2006 [als]   created
"""
__version__ = "$Revision: 1.3 $"[11:-2]
__date__ = "$Date: 2006/12/12 10:49:27 $"[7:-2]

__all__ = ["TextDriver"]

import math
import tkFont

from PythonReports import drivers

class TextDriver(drivers.TextDriver):

    """Text processing driver

    The driver is instantiated once for each report font
    and handles all texts printed out with that font.

    """

    backend = "Tk"

    def __init__(self, font):
        """Create text driver instance

        Parameters:
            font: report font definition (element instance)

        """
        # pylint: disable-msg=W0212
        # W0212: Access to a protected member _root of a client class -
        #   any ideas how to get fpixels another way?
        super(TextDriver, self).__init__(font)
        self._font = self._get_font(font)
        self.height = self._font["size"]
        # Tk fonts measure everything in pixels.  we need points.
        self._pointsize = self._font._root.winfo_fpixels("1p")
        # convert linespace to points.
        self._linespace = self._font.metrics("linespace") / self._pointsize
        self.leading = int(math.ceil(self._linespace - self.height))

    @staticmethod
    def _get_font(font):
        """Return tkFont.Font for given template/printout font element"""
        _attrs = {
            "family": font.get("typeface"),
            "size": font.get("size"),
            "weight": "normal",
            "slant": "roman",
            "underline": False,
        }
        for (_prop, _attr, _value) in (
            ("bold", "weight", "bold"),
            ("italic", "slant", "italic"),
            ("underline", "underline", True),
        ):
            if font.get(_prop, False):
                _attrs[_attr] = _value
        return tkFont.Font(**_attrs)

    def getsize(self, text):
        """Return size tuple (width, height) for given text"""
        _lines = text.split("\n")
        _height = int(math.ceil(self._linespace)) * len(_lines) - self.leading
        _width = int(math.ceil(
            max([self._font.measure(_line) for _line in _lines])
            / self._pointsize))
        return (_width, _height)

# vim: set et sts=4 sw=4 :
