"""Convert PythonReports printouts into s-reports printouts.

A printout is a built report: pages of marks with nothing left
to evaluate.  Both engines have one, and the two are close enough
that an archived PythonReports printout (.prp) can be carried over
to s-reports and rendered by its PDF writer, or kept in its format.

The conversion builds the printout model of s-reports,
so that s-reports writes the result and holds it to the invariants
of its format.  This module therefore needs the s-reports package,
which provides the sr library.

What changes on the way:

* Text.  PythonReports keeps the lines of a text block in one string
  and centers them in the box when it renders them.  s-reports keeps
  a list of lines, gives each line 1.2 times the font size, and places
  the first baseline by the face's own metrics, so the box is moved to
  put each baseline where PythonReports drew it.
* Fonts.  An s-reports printout names the font file each font was measured
  with.  That is the file PythonReports would find for the typeface,
  or the one s-reports finds where PythonReports finds none.
* Images that PythonReports cut to their box are drawn at their natural
  size from the bottom of the box, as PythonReports draws them.
* Bar code modules are converted from mils to points, and the box is
  sized by the stripes, which is how s-reports checks a bar code.
* Links inside an xref are positioned on the page rather than in the
  xref, and outline levels are written as depths in the outline tree.

"""

__all__ = ["Conversion", "convert", "font_file"]

import datetime
import math
import os
from pathlib import Path

from sr import meta
from sr.errors import BuildWarning, NodePath
from sr.fonts.face import open_face
from sr.fonts.resolve import Resolver
from sr.image import read_header
from sr.printout import model
from sr.printout.verify import check
from sr.template.model import Font

from PythonReports import fonts as pr_fonts
from PythonReports import printout as prp

# s-reports gives a line of text this much of its font size.
LEADING = 1.2

# Page margin attributes, in the order sr.printout.model.Paper takes them.
MARGINS = ("leftmargin", "rightmargin", "topmargin", "bottommargin")

# The patterns of a PythonReports pen that is not solid,
# which PythonReports draws one point wide.
DASHES = ("dot", "dash", "dashdot")

class Conversion(object):

    """The result of converting one printout

    Attributes:
        printout: the s-reports printout, as sr.printout.model.Printout.
        notes: list of strings: what did not carry over unchanged.

    """

    def __init__(self, printout, notes):
        self.printout = printout
        self.notes = notes

def convert(path, build_time=None):
    """Convert one printout file.

    Parameters:
        path: PythonReports printout file path.
        build_time: what the header records as the time the report was
            built, as a datetime.  PythonReports printouts do not say;
            the default is the time the file was last modified.

    Return value: a Conversion object.

    """
    _tree = prp.load(path)
    if build_time is None:
        build_time = datetime.datetime.fromtimestamp(os.path.getmtime(path),
            datetime.timezone.utc)
    return _Converter(path, _tree).run(build_time)

def _rounded(points):
    """Return points rounded as s-reports rounds them."""
    return round(points, 3) + 0.0

def _built(moment):
    """Return a datetime as the RFC 3339 text a header carries."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.timezone.utc)
    return moment.astimezone(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")

_FOUND = {}

def font_file(typeface, bold=False, italic=False):
    """Return the font file PythonReports measures a typeface with.

    Return value: a pair (path, step) where step is "host" when
    PythonReports knows the typeface, and "substitute" when it falls
    back to its default face.  None if PythonReports finds no file.

    """
    _key = (typeface, bool(bold), bool(italic))
    if _key in _FOUND:
        return _FOUND[_key]
    pr_fonts.add_windows_fonts()
    _known = _key in pr_fonts.FONTS
    try:
        _path = pr_fonts.fontfile(typeface, bold, italic)
    except IOError:
        _rv = None
    else:
        _rv = (os.path.abspath(_path), "host" if _known else "substitute")
    _FOUND[_key] = _rv
    return _rv

def _reportlab_ascent(path, index):
    """Return the ascent PythonReports' PDF writer places text by.

    The writer takes it from ReportLab, in thousandths of the size.
    Return None where ReportLab cannot read the face.

    """
    try:
        from reportlab.pdfbase import ttfonts
        return ttfonts.TTFontFile(path, subfontIndex=index).ascent / 1000.0
    except Exception:
        return None

class _Font(object):

    """One printout font, with what placing its text needs"""

    def __init__(self, entry, face):
        self.entry = entry
        self.face = face
        self.size = entry.size
        self.leading = round(self.size * LEADING, 3)
        _scale = float(self.size) / face.units_per_em
        # The face's own ascender and descender, the descender positive.
        self.ascender = face.ascent * _scale
        self.descender = -face.descent * _scale
        _ascent = None
        if entry.file is not None:
            _ascent = _ascent_of(entry.file, entry.index)
        self.pr_ascent = (_ascent * self.size) if _ascent is not None \
            else self.ascender

def _ascent_of(path, index):
    """Return the ReportLab ascent of a face file, cached."""
    _key = (str(path), index)
    if _key not in _ASCENTS:
        _ASCENTS[_key] = _reportlab_ascent(str(path), index)
    return _ASCENTS[_key]

_ASCENTS = {}

class _Converter(object):

    """The conversion of one printout"""

    def __init__(self, path, tree):
        self.path = path
        self.tree = tree
        self.root = tree.getroot()
        self.notes = []
        self.warnings = []
        self.fonts = {}
        self.used_fonts = set()
        self.data = {}
        self.data_names = {}
        self.resolver = None
        self.basedir = os.path.dirname(os.path.abspath(path))
        if self.root.get("basedir"):
            self.basedir = os.path.join(self.basedir,
                self.root.get("basedir"))
        self.named = {}
        for _element in self.root.findall("data"):
            self.named[_element.get("name")] = _element
        self.outline_names = set(_item.get("name")
            for _item in self.root.iter("outline"))
        self.targets = set(_item.get("target")
            for _item in self.root.iter("xref")
            if _item.get("type") == "outline")
        self.depths = []
        self.current_paper = None
        self.slack = dict.fromkeys(MARGINS, 0.0)

    def note(self, message):
        """Record a note once."""
        if message not in self.notes:
            self.notes.append(message)

    def run(self, build_time):
        """Return the Conversion of the printout."""
        _pages = self.root.findall("page")
        self.slack = self.margin_slack(_pages)
        _paper = self.paper(_pages[0])
        _converted = []
        for (_number, _page) in enumerate(_pages, 1):
            _own = self.paper(_page)
            self.current_paper = _own
            _marks = []
            for _element in _page:
                _marks.extend(self.marks(_element, 0, 0))
            _converted.append(model.Page(number=_number, marks=tuple(_marks),
                paper=None if _own == _paper else _own))
        _report = model.Report(**dict((_name, self.root.get(_name))
            for _name in ("name", "description", "version", "author")))
        _printout = model.Printout(
            report=_report,
            built=_built(build_time),
            engine=meta.engine(),
            strict_fonts=False,
            paper=_paper,
            fonts=tuple(self.fonts[_name].entry
                for _name in sorted(self.used_fonts)),
            data=dict((_name, self.data[_name])
                for _name in sorted(self.data)),
            pages=tuple(_converted),
            warnings=tuple(self.warnings),
        )
        _broken = check(_printout)
        if _broken and not any(_warning.kind == "overflow"
            for _warning in self.warnings
        ):
            # Marks PythonReports put outside the margins.  s-reports keeps
            # such a printout, with a warning that says so.
            _printout.warnings = _printout.warnings + (BuildWarning(
                "overflow", "marks lie outside the printable area: %s"
                % "; ".join(_broken[:3])),)
            self.note("marks lie outside the printable area, "
                "which the printout header now says")
            _broken = check(_printout)
        if _broken:
            raise ValueError("the converted printout breaks the invariants "
                "of the s-reports format: %s" % "; ".join(_broken))
        return Conversion(_printout, self.notes)

    def paper(self, page):
        """Return the paper geometry of a page, its margins eased."""
        _margins = [max(_rounded(page.get(_name) - self.slack[_name]), 0.0)
            for _name in MARGINS]
        return model.Paper(_rounded(page.get("width")),
            _rounded(page.get("height")), *_margins)

    def margin_slack(self, pages):
        """Return how far to ease each margin for the marks on the pages.

        PythonReports writes every dimension of a printout as a whole
        number of points, so a mark that reaches a margin may cross it
        by a fraction of a point once both are rounded.  s-reports checks
        that marks stay inside the margins, which nothing renders:
        the margin is eased by up to a point where a mark needs it.

        """
        _rv = dict.fromkeys(MARGINS, 0.0)
        for _page in pages:
            _right = _page.get("width") - _page.get("rightmargin")
            _bottom = _page.get("height") - _page.get("bottommargin")
            for (_left, _top, _width, _height) in self.extents(_page, 0, 0):
                for (_name, _excess) in (
                    ("leftmargin", _page.get("leftmargin") - _left),
                    ("rightmargin", _left + _width - _right),
                    ("topmargin", _page.get("topmargin") - _top),
                    ("bottommargin", _top + _height - _bottom),
                ):
                    if _excess > _rv[_name]:
                        _rv[_name] = _excess
        for _name in MARGINS:
            _excess = math.ceil(_rv[_name] * 1000) / 1000.0
            _rv[_name] = _excess if _excess <= 1.0 else 0.0
        return _rv

    def extents(self, container, left, top):
        """Yield (x, y, width, height) of every box in a container."""
        for _element in container:
            _box = _element.find("box")
            if _box is None:
                continue
            _left = _box.get("x") + left
            _top = _box.get("y") + top
            yield (_left, _top, _box.get("width"), _box.get("height"))
            if _element.tag == "xref":
                yield from self.extents(_element, _left, _top)

    # -- marks -----------------------------------------------------------

    def box(self, element, left, top):
        """Return the page box of an element inside an xref at left, top."""
        _box = element.find("box")
        return model.Box(_rounded(_box.get("x") + left),
            _rounded(_box.get("y") + top), _rounded(_box.get("width")),
            _rounded(_box.get("height")))

    def marks(self, element, left, top):
        """Return the s-reports marks for one printout element."""
        _handler = getattr(self, "mark_" + element.tag, None)
        if _handler is None:
            return []
        return _handler(element, left, top)

    def mark_text(self, element, left, top):
        """Return the marks of a text block.

        PythonReports puts the first baseline (H - L * (n - 1) + a) / 2
        below the top of a box H tall, with a leading L of 1.2 times
        the size and the ascent a that ReportLab reads.  s-reports puts it
        (L - (A + D)) / 2 + A below the top of its box, with A and D
        the face's ascender and descender.  The box moves so that every
        baseline stays where PythonReports drew it.

        The box of s-reports is a little taller than the one PythonReports
        had, which can take it past a margin the text is flush with.
        Then each line becomes a mark of its own, with a leading cut
        to the room there is: one line spaces nothing by its leading,
        and only places its baseline by it.

        """
        _content = element.find("data").text or ""
        _content = _content.replace("\r\n", "\n").replace("\n\r", "\n") \
            .replace("\r", "\n")
        if not _content:
            # PythonReports draws nothing for an empty block.
            return []
        _lines = tuple(_content.split("\n"))
        _font = self.font(element.get("font"))
        _box = self.box(element, left, top)
        _step = _font.size * LEADING
        _first = _box.y + (_box.height - _step * (len(_lines) - 1)
            + _font.pr_ascent) / 2.0
        _rise = _font.ascender - _font.descender
        _start = _first - (_font.leading + _rise) / 2.0
        _height = _rounded(_font.leading * len(_lines))
        _paper = self.current_paper
        _top = _paper.top
        _bottom = _paper.height - _paper.bottom
        _was_inside = (_box.y >= _top - 0.001) \
            and (_box.y + _box.height <= _bottom + 0.001)
        _is_inside = (_start >= _top - 0.001) \
            and (_start + _height <= _bottom + 0.001)
        if _is_inside or not _was_inside:
            return [self.text_mark(element, _box, _start, _font.leading,
                _lines)]
        _rv = []
        for (_idx, _line) in enumerate(_lines):
            _baseline = _first + _idx * _step
            _leading = min(_font.leading, 2 * (_baseline - _top) - _rise,
                2 * (_bottom - _baseline) + _rise)
            # Rounded down, so that the box stays inside.
            _leading = math.floor(_leading * 1000) / 1000.0
            if _leading <= 0:
                # The glyphs themselves reach past the margin.
                _leading = _font.leading
            _rv.append(self.text_mark(element, _box,
                _baseline - (_leading + _rise) / 2.0, _leading, (_line,)))
        return _rv

    def text_mark(self, element, box, top, leading, lines):
        """Return one text mark."""
        _align = str(element.get("align") or "left")
        return model.Text(
            box=model.Box(box.x, _rounded(top), box.width,
                _rounded(leading * len(lines))),
            font=str(element.get("font")),
            color=str(element.get("color")),
            align=_align,
            leading=_rounded(leading),
            lines=lines,
            # PythonReports spreads every line of justified text,
            # the last one included.
            last_line_justified=(_align == "justified"),
        )

    def mark_line(self, element, left, top):
        """Return the mark of a line."""
        (_width, _dash) = self.pen(element.get("pen"))
        if _width is None:
            return []
        _box = self.box(element, left, top)
        # PythonReports draws a sloped line rising, "/", unless told
        # backslant, and s-reports draws it falling, "\", unless told so.
        _sloped = (_box.width > 0) and (_box.height > 0)
        return [model.Line(box=_box, width=_width, dash=_dash,
            color=str(element.get("color")),
            backslant=_sloped and not element.get("backslant"))]

    def mark_rectangle(self, element, left, top):
        """Return the mark of a rectangle."""
        (_width, _dash) = self.pen(element.get("pen"))
        _fill = element.get("color")
        _stroke = None if _width is None else str(element.get("pencolor"))
        if (_stroke is None) and (_fill is None):
            return []
        return [model.Rectangle(box=self.box(element, left, top),
            width=0.0 if _width is None else _width,
            dash=_dash, stroke=_stroke,
            fill=None if _fill is None else str(_fill),
            radius=_rounded(element.get("radius") or 0))]

    def pen(self, pen):
        """Return the stroke width and dash pattern of a pen.

        The width is None for a pen that draws nothing.

        """
        if pen in DASHES:
            return (1.0, str(pen))
        if float(pen) == 0:
            return (None, "solid")
        return (_rounded(float(pen)), "solid")

    def mark_image(self, element, left, top):
        """Return the mark of an image."""
        _box = self.box(element, left, top)
        _data_child = element.find("data")
        _file = None
        _name = None
        if _data_child is not None:
            _bytes = prp.Data.get_data(_data_child)
            _name = self.blob(None, _bytes)
        elif element.get("data"):
            _named = element.get("data")
            _bytes = prp.Data.get_data(self.named[_named])
            _name = self.blob(_named, _bytes)
        else:
            _file = os.path.join(self.basedir, element.get("file"))
            if not os.path.exists(_file) \
            and os.path.exists(element.get("file")):
                _file = os.path.abspath(element.get("file"))
            with open(_file, "rb") as _stream:
                _bytes = _stream.read()
        _header = read_header(_bytes)
        if element.get("scale"):
            return [model.Image(box=_box, data=_name,
                file=None if _file is None else _as_path(_file))]
        # PythonReports cuts an image from its top left corner to the box,
        # and draws what is left at its natural size from the bottom left
        # corner of the box.
        _width = int(min(_box.width, _header.width))
        _height = int(min(_box.height, _header.height))
        return [model.Image(
            box=model.Box(_box.x, _rounded(_box.y + _box.height - _height),
                float(_width), float(_height)),
            data=_name,
            file=None if _file is None else _as_path(_file),
            crop=model.Crop(0.0, 0.0, float(_width), float(_height)),
        )]

    def blob(self, name, data):
        """Return the data table name an image's bytes are kept under.

        A named block keeps its name.  Anonymous bytes take "image",
        then "image-2" and so on, as s-reports names blobs, and bytes met
        twice are kept once.

        """
        if data in self.data_names:
            return self.data_names[data]
        if name is None:
            _base = "image"
            name = _base
            _count = 1
            while (name in self.data) or (name in self.named):
                _count += 1
                name = "%s-%i" % (_base, _count)
        self.data[name] = data
        self.data_names[data] = name
        return name

    def mark_barcode(self, element, left, top):
        """Return the mark of a bar code."""
        _box = self.box(element, left, top)
        _module = _rounded(float(element.get("module")) * 72.0 / 1000.0)
        _rows = []
        for _row in element.get("stripes").split():
            _runs = [int(_item) for _item in _row.split(",")]
            # s-reports ends a row with its last run, never an empty one.
            while (len(_runs) > 1) and (_runs[-1] == 0):
                _runs.pop()
            _rows.append(tuple(_runs))
        _type = str(element.get("type"))
        if len(_rows) == 1:
            _length = _rounded(sum(_rows[0]) * _module)
            _vertical = bool(element.get("vertical"))
            if _vertical:
                _symbol = model.Box(_box.x, _box.y, _box.width, _length)
            else:
                _symbol = model.Box(_box.x, _box.y, _length, _box.height)
            return [model.Barcode(box=_symbol, symbology=_type,
                value=element.get("value"), module=_module,
                vertical=_vertical, ink="#000000", paper="#FFFFFF",
                stripes=_rows[0])]
        _symbol = model.Box(_box.x, _box.y,
            _rounded(max(sum(_row) for _row in _rows) * _module),
            _rounded(len(_rows) * _module))
        return [model.Barcode(box=_symbol, symbology=_type,
            value=element.get("value"), module=_module, vertical=False,
            ink="#000000", paper="#FFFFFF", rows=tuple(_rows))]

    def mark_outline(self, element, left, top):
        """Return the mark of an outline entry."""
        _level = int(element.get("level") or 1)
        # The depth in the tree: one more than the nearest entry before
        # with a lower level, or 1 where there is none.
        while self.depths and (self.depths[-1][0] >= _level):
            self.depths.pop()
        _depth = (self.depths[-1][1] + 1) if self.depths else 1
        self.depths.append((_level, _depth))
        _name = element.get("name")
        return [model.Outline(
            box=model.Box(_rounded(element.get("x") + left),
                _rounded(element.get("y") + top), 0.0, 0.0),
            title=str(element.get("title")),
            level=_depth,
            name=_name if _name in self.targets else None,
            closed=bool(element.get("closed")),
        )]

    def mark_xref(self, element, left, top):
        """Return the mark of a link, with the marks inside it."""
        _box = self.box(element, left, top)
        _marks = []
        for _child in element:
            _marks.extend(self.marks(_child, _box.x, _box.y))
        _type = str(element.get("type"))
        _target = element.get("target")
        if (_type == "outline") and (_target not in self.outline_names):
            self.note("a link to the outline entry %r, which the printout "
                "does not have, is left out; what it held is kept" % _target)
            return _marks
        return [model.Xref(box=_box, link=_type, target=_target,
            caption=element.get("caption") or None, marks=tuple(_marks))]

    # -- fonts -----------------------------------------------------------

    def font(self, name):
        """Return the _Font for a printout font name, resolving it once."""
        self.used_fonts.add(name)
        if name in self.fonts:
            return self.fonts[name]
        _element = self.tree.fonts[name]
        _typeface = _element.get("typeface")
        _bold = bool(_element.get("bold"))
        _italic = bool(_element.get("italic"))
        _size = int(_element.get("size"))
        _underline = bool(_element.get("underline"))
        _found = font_file(_typeface, _bold, _italic)
        if _found is not None:
            (_path, _step) = _found
            _face = open_face(_as_path(_path), 0)
            if _step == "substitute":
                self.warnings.append(BuildWarning("font", "PythonReports "
                    "has no face for the typeface %r and measured the text "
                    "of font %r with %s" % (_typeface, name,
                        os.path.basename(_path))))
            _entry = model.FontEntry(name=name, size=_size, bold=_bold,
                italic=_italic, underline=_underline, face=_face.family,
                step=_step, requested=_typeface, file=_as_path(_path),
                index=0)
        else:
            # PythonReports finds no file here, so s-reports looks for one.
            if self.resolver is None:
                self.resolver = Resolver()
            _resolution = self.resolver.resolve(Font(name=name,
                typeface=_typeface, file=None, data=None, size=_size,
                bold=_bold, italic=_italic, underline=_underline,
                path=NodePath()))
            _face = _resolution.face
            self.warnings.extend(_resolution.warnings)
            self.note("PythonReports finds no font file for %r here; "
                "the text of font %r is drawn with %s, which s-reports found"
                % (_typeface, name, _face.origin.shown()))
            _entry = model.FontEntry(name=name, size=_size, bold=_bold,
                italic=_italic, underline=_underline, face=_face.family,
                step=_resolution.step, requested=_typeface,
                file=_face.origin.path, data=_face.origin.data,
                index=_face.origin.index or 0)
        _font = _Font(_entry, _face)
        self.fonts[name] = _font
        return _font

def _as_path(path):
    """Return a file path as the pathlib object s-reports holds."""
    return Path(path)

# vim: set et sts=4 sw=4 :
