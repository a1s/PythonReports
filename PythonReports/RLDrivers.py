"""Rendering utilities for ReportLab PDF library

This module contains no image driver: ReportLab requires PIL for images,
so we can just use PIL ImageDriver instead of wrapping a wrapper.

"""

__all__ = ["TextDriver"]

from reportlab.pdfbase import pdfmetrics, ttfonts

from PythonReports import drivers, fonts

class TextDriver(drivers.TextDriver):

    """Text processing driver

    The driver is instantiated once for each report font
    and handles all texts printed out with that font.

    """

    backend = "RL"

    # 1/5 of character size is default line gap used by ReportLab.
    DEFAULT_LEADING = .2

    # classwide singleton keeping a list of font names
    # that are registered with pdfmetrics
    _registered_fonts = set()

    def __init__(self, font):
        """Create text driver instance

        Parameters:
            font: report font definition (element instance)

        """
        super(TextDriver, self).__init__(font)
        _typeface = font.get("typeface")
        _size = font.get("size")
        _bold = font.get("bold")
        _italic = font.get("italic")
        _name = _typeface
        if _bold:
            _name += " Bold"
        if _italic:
            _name += " Italic"
        if _name not in self._registered_fonts:
            pdfmetrics.registerFont(ttfonts.TTFont(_name,
                fonts.fontfile(_typeface, _bold, _italic)))
            self._registered_fonts.add(_name)
        self.name = _name
        self.height = _size
        self.leading = _size * self.DEFAULT_LEADING

    def getsize(self, text):
        """Return size tuple (width, height) for given text"""
        # have to aggregate dimensions manually
        _lines = text.split("\n")
        _height = (self.height + self.leading) * len(_lines) - self.leading
        _width = max([pdfmetrics.stringWidth(_line, self.name, self.height)
            for _line in _lines])
        return (_width, _height)

# vim: set et sts=4 sw=4 :
