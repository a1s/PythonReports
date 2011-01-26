"""List installed TTF fonts on windows platform"""
"""History (most recent first):
26-jan-2011 [luch]  created
"""
__version__ = "$Revision: 1.1 $"[11:-2]
__date__ = "$Date: 2011/01/26 13:50:57 $"[7:-2]

def ls_ttf():
    """@return: mapping of C{(font name, bold, italic)} to C{TTF file name}.

    TTF font name ends with "(TrueType)" suffix and
    contains 0, 1 or 2 flags before it.

    C{bold} and C{italic} are boolean flags.
    C{font name} itself does not contain C{"Bold"} or C{"Italic"} words.

    C{TTF file name} is name under windows system fonts catalog without a path.

    """
    _rv = {}
    for (_name, _fn) in ls_fonts_key():
        _name = _name.split()
        if _name[-1] != "(TrueType)":
            continue

        del _name[-1]

        _italic = (_name[-1] in ("Italic", "Oblique"))
        if _italic:
            del _name[-1]
        _bold = (_name[-1] == "Bold")
        if _bold:
            del _name[-1]

        _rv[(" ".join(_name), _bold, _italic)] = _fn

    return _rv


try:
    import _winreg
except ImportError:
    def ls_fonts_key():
        return []
else:
    def ls_fonts_key():
        """@return: list of C{(font name, file name)} pairs from registry"""
        _FONTS_KEY = "SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        _key = None
        try:
            _key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, _FONTS_KEY)
            _nn = _winreg.QueryInfoKey(_key)[1]
            return [_winreg.EnumValue(_key, _ii)[:2] for _ii in xrange(_nn)]
        except WindowsError:
            if _key:
                _winreg.CloseKey(_key)
            return []


if __name__ == "__main__":
    import sys
    for ((_name, _bold, _italic), _ttf) in sorted(ls_ttf().iteritems()):
        sys.stdout.write("%s %s %s %s\n" % (
            _bold and "B" or " ", _italic and "I" or " ",
            _name.ljust(40, " "), _ttf))

# vim: set et sts=4 sw=4 :
