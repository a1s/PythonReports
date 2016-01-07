"""Fonts registry"""
"""History (most recent first):
26-jan-2011 [luch]  try to load windows fonts once when a font is missing
26-jan-2011 [als]   more well-known font file names;
                    add Mac OS X font paths
22-dec-2007 [als]   add Ubuntu fonts location to SYSFONTPATHS (sf bug 1856408)
27-sep-2006 [als]   support different system font path variants
26-sep-2006 [als]   add font paths on windows (required by reportlab)
26-sep-2006 [als]   created
"""
__version__ = "$Revision: 1.5 $"[11:-2]
__date__ = "$Date: 2011/01/26 13:53:59 $"[7:-2]

__all__ = ["fontfile", "register"]

from operator import itemgetter
import os, sys

import windows_fonts

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
    ("Consolas", False, False): "consola.ttf",
    ("Consolas", False, True): "consolai.ttf",
    ("Consolas", True, False): "consolab.ttf",
    ("Consolas", True, True): "consolaz.ttf",
    ("Courier New", False, False): "cour.ttf",
    ("Courier New", False, True): "couri.ttf",
    ("Courier New", True, False): "courbd.ttf",
    ("Courier New", True, True): "courbi.ttf",
    ("DejaVu Sans", False, False): "DejaVuSans.ttf",
    ("DejaVu Sans", False, True): "DejaVuSans-Oblique.ttf",
    ("DejaVu Sans", True, False): "DejaVuSans-Bold.ttf",
    ("DejaVu Sans", True, True): "DejaVuSans-BoldOblique.ttf",
    ("DejaVu Sans Condensed", False, False): "DejaVuSansCondensed.ttf",
    ("DejaVu Sans Condensed", False, True): "DejaVuSansCondensed-Oblique.ttf",
    ("DejaVu Sans Condensed", True, False): "DejaVuSansCondensed-Bold.ttf",
    ("DejaVu Sans Condensed", True, True):
        "DejaVuSansCondensed-BoldOblique.ttf",
    ("DejaVu Sans Mono", False, False): "DejaVuSansMono.ttf",
    ("DejaVu Sans Mono", False, True): "DejaVuSansMono-Oblique.ttf",
    ("DejaVu Sans Mono", True, False): "DejaVuSansMono-Bold.ttf",
    ("DejaVu Sans Mono", True, True): "DejaVuSansMono-BoldOblique.ttf",
    ("DejaVu Serif", False, False): "DejaVuSerif.ttf",
    ("DejaVu Serif", False, True): "DejaVuSerif-Italic.ttf",
    ("DejaVu Serif", True, False): "DejaVuSerif-Bold.ttf",
    ("DejaVu Serif", True, True): "DejaVuSerif-BoldItalic.ttf",
    ("DejaVu Serif Condensed", False, False): "DejaVuSerifCondensed.ttf",
    ("DejaVu Serif Condensed", False, True): "DejaVuSerifCondensed-Italic.ttf",
    ("DejaVu Serif Condensed", True, False): "DejaVuSerifCondensed-Bold.ttf",
    ("DejaVu Serif Condensed", True, True):
        "DejaVuSerifCondensed-BoldItalic.ttf",
    ("Tahoma", False, False): "tahoma.ttf",
    ("Tahoma", False, True): "tahoma.ttf",
    ("Tahoma", True, False): "tahomabd.ttf",
    ("Tahoma", True, True): "tahomabd.ttf",
    ("Times New Roman", False, False): "times.ttf",
    ("Times New Roman", False, True): "timesi.ttf",
    ("Times New Roman", True, False): "timesbd.ttf",
    ("Times New Roman", True, True): "timesbi.ttf",
    ("Trebuchet MS", False, False): "trebuc.ttf",
    ("Trebuchet MS", False, True): "trebucit.ttf",
    ("Trebuchet MS", True, False): "trebucbd.ttf",
    ("Trebuchet MS", True, True): "trebucbi.ttf",
    ("Verdana", False, False): "verdana.ttf",
    ("Verdana", False, True): "verdanai.ttf",
    ("Verdana", True, False): "verdanab.ttf",
    ("Verdana", True, True): "verdanaz.ttf",
    # if the font is not known to us, use monospaced font
    # for high estimate of the text width
    None: "cour.ttf",
}

WINDOWS_FONTS_ADDED = False

# paths to look for TrueType fonts
SYSFONTPATHS = []
if os.name == "nt":
    # MS Windows
    SYSFONTPATHS.append(os.path.join(os.getenv("WINDIR"), "Fonts"))
elif os.name == "posix":
    # X windows
    SYSFONTPATHS.append("/usr/X11R6/lib/X11/fonts/TrueType")
    SYSFONTPATHS.extend(map(itemgetter(0), os.walk("/usr/share/fonts")))
    SYSFONTPATHS.extend(map(itemgetter(0), os.walk("/usr/local/share/fonts")))
    if sys.platform == "darwin":
        SYSFONTPATHS.extend(map(itemgetter(0), os.walk("/Library/Fonts")))
        FONTS[None] = "Courier New.ttf"

def fontfile(typeface, bold=False, italic=False):
    """Return TTF file name for a font

    Parameters:
        typeface: font name
        bold: True for bold font
        italic: True for italic font

    """
    _font_key = (typeface, bool(bold), bool(italic))
    try:
        _file = FONTS[_font_key]
    except KeyError:
        add_windows_fonts()
        try:
            _file = FONTS[_font_key]
        except:
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
                FONTS[_font_key] = _file
                break
        else:
            # PIL raises IOError when font file does not exist.  so do we.
            raise IOError("Cannot locate font file %r" % _file)
    return _file

def add_windows_fonts():
    """Register installed windows fonts"""
    global WINDOWS_FONTS_ADDED
    if not WINDOWS_FONTS_ADDED:
        FONTS.update(windows_fonts.ls_ttf())
        WINDOWS_FONTS_ADDED = True

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
