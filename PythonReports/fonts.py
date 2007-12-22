"""Fonts registry"""
"""History (most recent first):
22-dec-2007 [als]   add Ubuntu fonts location to SYSFONTPATHS (sf bug 1856408)
27-sep-2006 [als]   support different system font path variants
26-sep-2006 [als]   add font paths on windows (required by reportlab)
26-sep-2006 [als]   created
"""
__version__ = "$Revision: 1.3 $"[11:-2]
__date__ = "$Date: 2007/12/22 17:54:15 $"[7:-2]

__all__ = ["fontfile", "register"]

import os

# paths to look for TrueType fonts
if os.name == "nt":
    # MS Windows
    SYSFONTPATHS = [os.path.join(os.getenv("windir"), "Fonts")]
elif os.name == "posix":
    # X windows
    SYSFONTPATHS = [
        "/usr/X11R6/lib/X11/fonts/TrueType",
        "/usr/share/fonts/corefonts", # Gentoo Linux (TM)
        "/usr/share/fonts/truetype/msttcorefonts", # Ubuntu (Feisty)
    ]

# well-known font files
FONTS = {
    ("Arial", False, False): "arial.ttf",
    ("Arial", False, True): "ariali.ttf",
    ("Arial", True, False): "arialbd.ttf",
    ("Arial", True, True): "arialbi.ttf",
    ("Comic Sans MS", False, False): "comic.ttf",
    ("Comic Sans MS", False, True): "comic.ttf",
    ("Comic Sans MS", True, False): "comicbd.ttf",
    ("Comic Sans MS", True, True): "comicbd.ttf",
    ("Courier New", False, False): "cour.ttf",
    ("Courier New", False, True): "couri.ttf",
    ("Courier New", True, False): "courbd.ttf",
    ("Courier New", True, True): "courbi.ttf",
    ("Times New Roman", False, False): "times.ttf",
    ("Times New Roman", False, True): "timesi.ttf",
    ("Times New Roman", True, False): "timesbd.ttf",
    ("Times New Roman", True, True): "timesbi.ttf",
    # if the font is not known to us, use monospaced font
    # for high estimate of the text width
    None: "cour.ttf",
}

def fontfile(typeface, bold=False, italic=False):
    """Return TTF file name for a font

    Parameters:
        typeface: font name
        bold: True for bold font
        italic: True for italic font

    """
    try:
        _file = FONTS[(typeface, bool(bold), bool(italic))]
    except KeyError:
        _file = FONTS[None]
    if os.path.dirname(_file) == "":
        # file name does not contain directory path.
        # the font must be in the system fonts directory.
        for _dir in SYSFONTPATHS:
            _candidate = os.path.join(_dir, _file)
            if os.path.isfile(_candidate):
                _file = _candidate
                # replace file name in the global registry
                # to skip the search next time
                # WARNING: this will populate the registry
                # with default font for each unknown typeface
                FONTS[(typeface, bool(bold), bool(italic))] = _file
                break
        else:
            # PIL raises IOError when font file does not exist.  so do we.
            raise IOError("Cannot locate font file %r" % _file)
    return _file

def register(filename, typeface, bold=False, italic=False):
    """Register non-standard TTF file

    Parameters:
        filename: font file name.
            If the font is not in the system fonts directory,
            must include file path.
        typeface: font name.
        bold: True for bold font.
        italic: True for italic font.

    """
    FONTS[(typeface, bool(bold), bool(italic))] = filename

# vim: set et sts=4 sw=4 :
