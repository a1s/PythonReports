"""Convert PythonReports templates into s-reports templates.

The two formats are close relatives:
the template format of s-reports was designed after this one,
and most elements keep their names and their meaning.
This module converts a template in either PythonReports syntax,
XML (.prt) or RSON (.prtr), into an s-reports template in KDL (.kdl),
and lists everything it could not carry over unchanged.

What changes on the way:

* Geometry.  A PythonReports element has a box child with x, y,
  width and height, where negative values count from the far edge
  of the container.  An s-reports element takes left, right, top, bottom,
  width and height properties, any two per axis.  Lines and rectangles
  spend "width" on the stroke, so their extent is given by left and
  right, and those need the width of the container, which is computed
  from the page geometry.
* Alignment.  PythonReports aligns the content of a field, an image
  or a bar code to the bottom of its box unless told otherwise; s-reports
  aligns it to the top.  The converted element says "bottom".
* Styles.  The "printwhen" of a style becomes the "printwhen" of the
  element or section, since s-reports keeps it there.
* Values.  Colors are written as #RRGGBB, since the two formats give
  some color names different values.  Pens become a stroke width and
  a dash pattern, bar code modules a dimension in mils, and data blocks
  base64, compressed with zlib where the original was compressed.
* Expressions are translated by the expressions module.
* Records.  s-reports declares the fields of the data records, with types.
  The converter declares every field the expressions read; the types
  come from sample data where it is given, and are guessed from use
  otherwise.

"""

__all__ = ["Conversion", "Note", "convert", "load_raw"]

import ast
import base64
import copy
import json
import os
import re
import xml.etree.ElementTree as ET
import zlib

from PythonReports import datatypes
from PythonReports import template as prt
from PythonReports.migrate import kdl
from PythonReports.migrate.expressions import CONVERSION, Names, \
    STARLARK_KEYWORDS, SR_GLOBALS, SR_PREDEFINED, Translator, \
    engine_format, format_hints, starlark

# What a converted template file is named after: the source with this.
EXTENSION = ".kdl"

# Template file extensions that a subreport reference is renamed from.
SOURCE_EXTENSIONS = (".prt", ".prtr", ".xml")

# The prefix of every comment the converter writes into a template.
MARK = "migrate:"

# The number syntax s-reports reads in a dimension.
_DIMENSION = re.compile(r"^\s*([+-]?(?:\d(?:_?\d)*(?:\.(?:\d(?:_?\d)*)?)?"
    r"|\.\d(?:_?\d)*)(?:[eE][+-]?\d(?:_?\d)*)?)\s*(pt|mm|cm|in)?\s*$")

# RFC 3339 dates and times, for guessing types from sample data.
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$")

# Element kinds that put marks on a page.
BODY = ("field", "line", "rectangle", "image", "barcode")

class Note(object):

    """Something the converter could not carry over unchanged

    Attributes:
        path: where in the template the note belongs,
            as a path of element names.
        message: what happened.

    """

    __slots__ = ["path", "message"]

    def __init__(self, path, message):
        self.path = path
        self.message = message

    def __str__(self):
        return "%s: %s" % (self.path, self.message)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self)

class Conversion(object):

    """The result of converting one template

    Attributes:
        text: the s-reports template, as KDL text.
        notes: list of Note objects.
        subreports: list of (source, target) pairs: the template files
            named by subreport elements, and the names the converted
            template refers to them by.

    """

    def __init__(self, text, notes, subreports):
        self.text = text
        self.notes = notes
        self.subreports = subreports

def load_raw(path):
    """Return the root element of a template file, as written.

    The file may be XML or RSON, told apart by its first character
    as PythonReports does.  The template is validated by PythonReports'
    own rules, but the tree returned holds the attributes as they were
    written, without the defaults validation fills in, so that the
    converter can tell what the author asked for.

    Parameters:
        path: template file path.

    """
    with open(path, "rb") as _file:
        _contents = _file.read()
    _match = re.match(rb"(?:\xEF\xBB\xBF|\xFF\xFE|\xFE\xFF)?\s*(\S)",
        _contents)
    if _match and (_match.group(1) == b"<"):
        _root = ET.fromstring(_contents)
    else:
        # Imported here: RSON needs rsonlite, and XML does not.
        import rsonlite
        from PythonReports import rson
        if _contents.startswith(b"\xFF\xFE"):
            _text = _contents.decode("utf-16-le")
        elif _contents.startswith(b"\xFE\xFF"):
            _text = _contents.decode("utf-16-be")
        else:
            _text = _contents.decode("utf-8")
        if _text.startswith("\ufeff"):
            _text = _text[1:]
        _root = _plain(rson.rson2element(prt.Report.tag,
            rsonlite.loads(_text)))
    _tree = datatypes.ElementTree(prt.Report, copy.deepcopy(_root))
    _tree.filename = path
    _tree.validate()
    return _root

def _plain(element):
    """Return a copy of an element tree holding plain strings.

    The RSON parser gives tokens that are subclasses of str,
    and keep where they were found; those do not copy.

    """
    _rv = ET.Element(str(element.tag), dict((str(_key), str(_value))
        for (_key, _value) in element.attrib.items()))
    if element.text is not None:
        _rv.text = str(element.text)
    for _child in element:
        _rv.append(_plain(_child))
    return _rv

def convert(path, records=None):
    """Convert one template file.

    Parameters:
        path: template file path, XML or RSON.
        records: optional sequence of sample data records: mappings,
            as JSON gives them, or objects with attributes.  Used to
            choose the types of the record fields the template reads.

    Return value: a Conversion object.

    """
    _root = load_raw(path)
    _converter = _Converter(path, records)
    _report = _converter.report(_root)
    _comments = [
        "Converted from %s by PythonReports.migrate."
            % os.path.basename(path),
        "Comments that begin with \"%s\" mark what did not carry over "
            "unchanged." % MARK,
    ]
    return Conversion(kdl.dumps([_report], _comments), _converter.notes,
        _converter.subreports)

# -- values -----------------------------------------------------------------

def _points(text):
    """Return a dimension as a number of points."""
    return float(datatypes.Dimension(text))

def _rounded(points):
    """Return points rounded as s-reports rounds them, as an int or float."""
    _value = round(points, 3) + 0.0
    if _value == int(_value):
        return int(_value)
    return _value

def _dimension(text):
    """Return a dimension the way s-reports should read it.

    A value s-reports reads the same way is kept as written, so that
    "5mm" stays "5mm".  Anything else becomes a number of points.

    """
    _match = _DIMENSION.match(text)
    if _match:
        if _match.group(2):
            return text.strip()
        _number = float(_match.group(1).replace("_", ""))
        return _rounded(_number)
    return _rounded(_points(text))

def _boolean(text):
    """Return a boolean attribute value as PythonReports reads it."""
    return bool(datatypes.Boolean(text))

def _color(text):
    """Return a color as #RRGGBB, the way PythonReports reads it."""
    return datatypes.Color.encode(text.strip())

def _data_bytes(element):
    """Return the contents of a data element, decoded."""
    return datatypes.DataBlock.get_data(element)

def _text_of(element):
    """Return the contents of a data element as text."""
    _data = _data_bytes(element)
    if _data is None:
        return ""
    if isinstance(_data, bytes):
        return _data.decode("utf-8", "replace")
    return str(_data)

def _base64_lines(data):
    """Return bytes as base64 text, broken into lines of 76."""
    _text = base64.b64encode(data).decode("ascii")
    return "\n".join(_text[_idx:_idx + 76]
        for _idx in range(0, len(_text), 76))

def _placeholder(spec):
    """Return a guess at the widest text a % format produces.

    Each conversion becomes a run of nines, which are as wide as
    any digit in most faces, and which every bar code type encodes.

    """
    def _sample(match):
        _verb = match.group("verb")
        if _verb == "%":
            return "%"
        if _verb in "eEfFgG":
            return "999999.99"
        return "9999"
    return CONVERSION.sub(_sample, spec)

def _is_true(text):
    """Return True if an expression is missing or the constant True."""
    return (text is None) or (text.strip() in ("", "True", "1"))

def _renamed(name, used):
    """Return the name to declare in s-reports, and whether it changed."""
    _new = name
    while (_new in SR_PREDEFINED) or (_new in SR_GLOBALS) \
    or (_new in STARLARK_KEYWORDS) or _new.startswith("_sr_") \
    or (_new in used):
        _new += "_"
    return _new

def _sample_type(values):
    """Return the s-reports type that sample values fit, and nulls."""
    _kinds = set()
    _nullable = False
    for _value in values:
        if _value is None:
            _nullable = True
        elif isinstance(_value, bool):
            _kinds.add("bool")
        elif isinstance(_value, int):
            _kinds.add("int")
        elif isinstance(_value, float):
            _kinds.add("float")
        elif isinstance(_value, str):
            if _DATETIME.match(_value):
                _kinds.add("datetime")
            elif _DATE.match(_value):
                _kinds.add("date")
            else:
                _kinds.add("string")
        elif isinstance(_value, dict) or hasattr(_value, "__dict__") \
        and not isinstance(_value, (list, tuple)):
            _kinds.add(_python_type(_value) or "object")
        elif isinstance(_value, (list, tuple)):
            _kinds.add("list")
        else:
            _kinds.add(_python_type(_value) or "string")
    if _kinds == set(("int", "float")):
        _kinds = set(("float",))
    if _kinds == set(("date", "datetime")):
        _kinds = set(("datetime",))
    if len(_kinds) == 1:
        return (_kinds.pop(), _nullable)
    if not _kinds:
        return (None, _nullable)
    return ("string", _nullable)

def _python_type(value):
    """Return the s-reports type of a Python value from a data sequence."""
    _name = type(value).__name__
    if _name == "datetime":
        return "datetime"
    if _name == "date":
        return "date"
    if _name == "Decimal":
        return "decimal"
    if isinstance(value, dict):
        return "object"
    return None

def _span(position, size):
    """Return how far a box reaches along one axis, where that is fixed.

    A box with a size of its own reaches that far.  A box placed from
    the far edge with a negative size reaches from its position to the
    edge its size names.  A box placed from the near edge with a negative
    size reaches as far as the container does, which is not known here:
    the result is None.

    """
    if size >= 0:
        return size
    if position < 0:
        return max(size - position, 0)
    return None

def _field_of(record, name):
    """Return a field of a sample record, mapping or object, or a marker."""
    try:
        return record[name]
    except (TypeError, KeyError, IndexError, AttributeError):
        return getattr(record, name, _MISSING)

_MISSING = object()

# -- the converter ----------------------------------------------------------

class _Scope(object):

    """A layout with names of its own: the report, or an embedded one"""

    def __init__(self, path, samples):
        self.names = Names()
        self.translator = Translator(self.names)
        # Variable names, as expressions write them, and their calc.
        self.calcs = {}
        self.path = path
        self.samples = samples

class _Converter(object):

    """The conversion of one template"""

    def __init__(self, path, records):
        self.path = path
        self.notes = []
        self.subreports = []
        self.datablocks = {}
        self.fonts = {}
        self.samples = list(records) if records is not None else None
        self.scope = None
        self.embedded_samples = {}
        self.outline_names = set()
        self.outline_targets = []
        self.basedir = None
        self.page = None

    def note(self, path, message, node=None):
        """Record a note, and write it above a node of the template."""
        if not any((_item.path, _item.message) == (path, message)
            for _item in self.notes
        ):
            self.notes.append(Note(path, message))
        if node is not None:
            _comment = "%s %s" % (MARK, message)
            if _comment not in node.comments:
                node.note(_comment)

    def expression(self, path, source, node=None, deferred=False,
        hint=None
    ):
        """Return the translation of an expression, noting its notes."""
        _result = self.scope.translator.translate(source, deferred, hint)
        for _message in _result.notes:
            self.note(path, "%s: %s" % (source.strip(), _message), node)
        return _result

    def expr_text(self, path, source, node=None, hint=None):
        """Return the translated text of an expression."""
        return self.expression(path, source, node, hint=hint).text

    # -- the report ------------------------------------------------------

    def report(self, root):
        """Return the report node for the root of a template."""
        _node = kdl.Node("report")
        self.basedir = root.get("basedir")
        for _name in ("name", "description", "version", "author",
            "basedir"
        ):
            if root.get(_name):
                _node.set(_name, root.get(_name))
        for _child in root.findall("data"):
            self.datablocks[_child.get("name")] = _child
        for _child in root.findall("font"):
            self.fonts[_child.get("name")] = _child
        _layout = root.find("layout")
        self.page = self.page_geometry(_layout)
        self.scope = _Scope("report", self.samples)
        _names = self.scope.names
        for _child in root.findall("import"):
            _path = _child.get("path").strip()
            _alias = _child.get("alias") or _path.rsplit(".", 1)[-1]
            _names.imports[_alias] = _path
        self.declare(root, _layout, self.scope)
        for _child in root.findall("import"):
            self.note("report/import", "s-reports has no imports: "
                "the expressions that used %s are rewritten where "
                "s-reports has a counterpart, and noted where it has "
                "none" % _child.get("path"), _node)
        _parameters = [self.parameter(_child, self.scope)
            for _child in root.findall("parameter")]
        _variables = [self.variable(_child, self.scope)
            for _child in root.findall("variable")]
        _fonts = [self.font(_child) for _child in root.findall("font")]
        _data = [self.datablock(_child) for _child in root.findall("data")]
        _layout_node = self.layout(_layout)
        _node.children.extend(_parameters)
        _records = self.records(self.scope)
        if _records is not None:
            _node.add(_records)
        _node.children.extend(_variables)
        _node.children.extend(_fonts)
        _node.children.extend(_data)
        _layout_node.blank = bool(_node.children)
        _node.add(_layout_node)
        for (_path, _target, _xref) in self.outline_targets:
            if _target not in self.outline_names:
                self.note(_path, "no outline in this template is named %r, "
                    "and s-reports refuses a link to an outline that is not "
                    "there: give the outline it should go to name=\"%r\""
                    % (_target, _target), _xref)
        return _node

    def declare(self, root, layout, scope):
        """Register the names a layout declares in its scope."""
        _names = scope.names
        _used = set()
        for _child in root.findall("parameter"):
            _old = _child.get("name")
            _new = _renamed(_old, _used)
            _used.add(_new)
            _names.parameters[_old] = _new
            if _new != _old:
                self.note("%s/parameter[%s]" % (scope.path, _old),
                    "renamed to %s: s-reports has a name %s of its own"
                    % (_new, _old))
        for _child in root.findall("variable"):
            _old = _child.get("name")
            _new = _renamed(_old, _used)
            _used.add(_new)
            _names.variables[_old] = _new
            if _new != _old:
                self.note("%s/variable[%s]" % (scope.path, _old),
                    "renamed to %s: s-reports has a name %s of its own"
                    % (_new, _old))
            _calc = (_child.get("calc") or "first").strip()
            scope.calcs[_old] = _calc
            if _calc == "count":
                _names.counted.add(_old)
        _names.groups.update(self.group_names(layout))

    def group_names(self, element):
        """Return the names of the groups nested in a layout element."""
        _rv = []
        _group = element.find("group")
        while _group is not None:
            _rv.append(_group.get("name"))
            _group = _group.find("group")
        return _rv

    def page_geometry(self, layout):
        """Return the page width and the frame width, in points."""
        _size = layout.get("pagesize")
        if _size:
            (_width, _height) = datatypes.PageSize.DIMENSIONS[_size.strip()]
        else:
            (_width, _height) = (_points(layout.get("width")),
                _points(layout.get("height")))
        if _boolean(layout.get("landscape") or "false"):
            (_width, _height) = (_height, _width)
        _margins = sum(_points(layout.get(_name) or "0")
            for _name in ("leftmargin", "rightmargin"))
        return float(_width) - _margins

    # -- declarations ----------------------------------------------------

    def parameter(self, element, scope):
        """Return the node of a parameter element."""
        _old = element.get("name")
        _path = "%s/parameter[%s]" % (scope.path, _old)
        _node = kdl.Node("parameter", scope.names.parameters[_old])
        _default = element.get("default") or ""
        try:
            _value = ast.literal_eval(_default.strip())
        except (ValueError, TypeError, SyntaxError, MemoryError,
            RecursionError
        ):
            (_value, _literal) = (None, False)
        else:
            _literal = True
        if _literal and isinstance(_value, str):
            _node.set("default", _value)
        elif _literal and isinstance(_value, bool):
            _node.set("type", "bool").set("default",
                "true" if _value else "false")
        elif _literal and isinstance(_value, int):
            _node.set("type", "int").set("default", str(_value))
        elif _literal and isinstance(_value, float):
            _node.set("type", "float").set("default", repr(_value))
        elif _literal and (_value is None):
            _node.set("default", "")
            self.note(_path, "the default None has no counterpart "
                "in s-reports, where a parameter has a type: "
                "it became an empty string", _node)
        elif _literal and isinstance(_value, (list, tuple, dict)):
            _node.set("type", "object" if isinstance(_value, dict)
                else "list")
            try:
                _node.set("default", json.dumps(_value))
            except (TypeError, ValueError):
                _node.set("defaultexpr", self.expr_text(_path, _default,
                    _node))
        else:
            _result = self.expression(_path, _default, _node)
            _kind = self.expression_type(_result)
            if _kind:
                _node.set("type", _kind)
            else:
                self.note(_path, "the type of the default %s is not known: "
                    "give the parameter the type that expression has"
                    % _default.strip(), _node)
            _node.set("defaultexpr", _result.text)
        if element.get("prompt") and _boolean(element.get("prompt")):
            _node.set("prompt", True)
        return _node

    def expression_type(self, result):
        """Return the s-reports type a translated expression evidently has."""
        _tree = result.tree
        if isinstance(_tree, ast.Name) and (_tree.id == "BUILD_TIME"):
            return "datetime"
        if isinstance(_tree, ast.Call):
            _func = _tree.func
            if isinstance(_func, ast.Name) and (_func.id == "decimal"):
                return "decimal"
            if isinstance(_func, ast.Attribute) and (_func.attr == "time") \
            and isinstance(_func.value, ast.Name) \
            and (_func.value.id == "time"):
                return "datetime"
        return None

    def variable(self, element, scope):
        """Return the node of a variable element."""
        _old = element.get("name")
        _path = "%s/variable[%s]" % (scope.path, _old)
        _names = scope.names
        _node = kdl.Node("variable", _names.variables[_old])
        _calc = (element.get("calc") or "first").strip()
        # A record field that is summed or averaged holds numbers.
        _node.set("expr", self.expr_text(_path, element.get("expr"), _node,
            hint="decimal" if _calc in ("sum", "avg", "std", "var") else None))
        if element.get("init"):
            _node.set("init", self.expr_text(_path, element.get("init"),
                _node))
        if _calc == "count":
            _calc = "set"
            self.note(_path, "PythonReports counts distinct values; "
                "the variable became a set, and the expressions that read it "
                "read its length", _node)
        elif _calc in ("std", "var"):
            self.note(_path, "s-reports computes the sample %s, dividing by "
                "n - 1, and PythonReports divides by n" % (
                    "standard deviation" if _calc == "std" else "variance"),
                _node)
        if _calc != "first":
            _node.set("calc", _calc)
        for (_attr, _group_attr, _default) in (
            ("iter", "itergrp", "detail"),
            ("reset", "resetgrp", "report"),
        ):
            _value = (element.get(_attr) or _default).strip()
            if _value != _default:
                _node.set(_attr, _value)
            if (_value == "group") and element.get(_group_attr):
                _node.set(_group_attr, element.get(_group_attr))
        return _node

    def font(self, element):
        """Return the node of a font element."""
        _node = kdl.Node("font", element.get("name"))
        _node.set("typeface", element.get("typeface"))
        _node.set("size", int(datatypes.Integer(element.get("size"))))
        for _name in ("bold", "italic", "underline"):
            if element.get(_name) and _boolean(element.get(_name)):
                _node.set(_name, True)
        return _node

    def datablock(self, element):
        """Return the node of a named data element."""
        _name = element.get("name")
        _path = "report/data[%s]" % _name
        _node = kdl.Node("data", _name)
        if element.get("expr"):
            _node.set("expr", self.expr_text(_path, element.get("expr"),
                _node))
            return _node
        if element.get("pickle") and _boolean(element.get("pickle")):
            _node.disabled = True
            self.note(_path, "the data block holds a pickled Python object, "
                "which s-reports cannot read", _node)
            return _node
        try:
            _data = _data_bytes(element)
        except Exception as _error:
            _node.disabled = True
            self.note(_path, "the data block does not decode: %s" % _error,
                _node)
            return _node
        if isinstance(_data, str) and not element.get("encoding"):
            _node.add(kdl.Node("content", _data))
            return _node
        if _data is None:
            _data = b""
        elif isinstance(_data, str):
            _data = _data.encode("utf-8")
        _node.set("encoding", "base64")
        if element.get("compress"):
            _node.set("compress", "zlib")
            _data = zlib.compress(_data, 9)
        _node.add(kdl.Node("content", kdl.Multiline(_base64_lines(_data))))
        return _node

    def records(self, scope):
        """Return the records node for the fields expressions read."""
        _fields = scope.names.records
        if not _fields:
            return None
        _node = kdl.Node("records")
        _guessed = False
        _missing = []
        for (_name, _hints) in _fields.items():
            _member = _node.add(kdl.Node("member", _name))
            _kind = None
            _nullable = False
            if scope.samples:
                _values = [_field_of(_record, _name)
                    for _record in scope.samples]
                _values = [_value for _value in _values
                    if _value is not _MISSING]
                if _values:
                    (_kind, _nullable) = _sample_type(_values)
                else:
                    _missing.append(_name)
            if _kind is None:
                _guessed = True
                # A decimal holds whatever an int does, so it goes first.
                _kind = ([_item for _item in ("datetime", "list", "object",
                    "decimal", "int") if _item in _hints] + ["string"])[0]
            if _kind != "string":
                _member.set("type", _kind)
            # The samples may lack the nulls that a test for one expects.
            if _nullable or ("nullable" in _hints):
                _member.set("nullable", True)
        if _missing:
            self.note("%s/records" % scope.path, "the sample data has no "
                "values for %s" % ", ".join(_missing), _node)
        if _guessed:
            self.note("%s/records" % scope.path, "the types of these fields "
                "are guessed from how the expressions use them, and a field "
                "they test for None or for truth is nullable: check them "
                "against the data, and mark the other fields that can be "
                "null nullable", _node)
        return _node

    # -- layouts ---------------------------------------------------------

    def layout(self, element):
        """Return the node of the layout element."""
        _node = kdl.Node("layout")
        if element.get("pagesize"):
            _node.set("pagesize", element.get("pagesize").strip())
        else:
            for _name in ("width", "height"):
                _node.set(_name, _dimension(element.get(_name)))
        if element.get("landscape") and _boolean(element.get("landscape")):
            _node.set("landscape", True)
        for _name in ("leftmargin", "rightmargin", "topmargin",
            "bottommargin"
        ):
            _value = element.get(_name)
            if _value and (_points(_value) != 0):
                _node.set(_name, _dimension(_value))
        _context = _Context(self, "layout", [element], self.page)
        self.collect_samples(element)
        _node.children.extend(self.styles(element, _context))
        for _child in element.findall("embedded"):
            _node.add(self.embedded(_child, _context))
        self.nesting(element, _node, _context, layout=True)
        return _node

    def embedded(self, element, context):
        """Return the node of an embedded subreport layout."""
        _name = element.get("name")
        _path = "%s/embedded[%s]" % (context.path, _name)
        _outer = self.scope
        _samples = self.embedded_samples.get(_name)
        self.scope = _Scope(_path, _samples)
        _names = self.scope.names
        _names.imports.update(_outer.names.imports)
        try:
            self.declare(element, element, self.scope)
            _node = kdl.Node("embedded", _name)
            _node.blank = True
            _parameters = [self.parameter(_child, self.scope)
                for _child in element.findall("parameter")]
            _variables = [self.variable(_child, self.scope)
                for _child in element.findall("variable")]
            _context = _Context(self, _path, [element], self.page)
            self.collect_samples(element)
            _body = self.styles(element, _context)
            for _child in element.findall("embedded"):
                _body.append(self.embedded(_child, _context))
            _holder = kdl.Node("embedded")
            self.nesting(element, _holder, _context, layout=True,
                inline=True)
            _body.extend(_holder.children)
            _node.children.extend(_parameters)
            _records = self.records(self.scope)
            if _records is not None:
                _node.add(_records)
            _node.children.extend(_variables)
            _node.children.extend(_body)
        finally:
            self.scope = _outer
        return _node

    def collect_samples(self, element):
        """Gather sample records for the embedded layouts a layout runs.

        A subreport whose data is a field of the record runs over
        what that field holds, so the samples of an embedded layout
        are the values of that field in the samples of this one.

        """
        if not self.scope.samples:
            return
        _pending = list(element)
        while _pending:
            _child = _pending.pop(0)
            if _child.tag == "embedded":
                continue
            _pending.extend(_child)
            if (_child.tag != "subreport") or not _child.get("embedded"):
                continue
            _field = (_child.get("data") or "").strip()
            if not _field.isidentifier():
                continue
            _samples = self.embedded_samples.setdefault(
                _child.get("embedded").strip(), [])
            for _record in self.scope.samples:
                _value = _field_of(_record, _field)
                if isinstance(_value, (list, tuple)):
                    _samples.extend(_value)

    def nesting(self, element, node, context, layout=False, inline=False):
        """Convert the bands and groups of a layout, group or embedded."""
        _sections = []
        for _kind in ("title", "summary") + (("header", "footer")
            if layout else ()
        ):
            _child = element.find(_kind)
            if _child is not None:
                _sections.append((_kind, _child))
        if inline:
            _sections = self.inline_bands(_sections, context)
        for (_kind, _child) in _sections:
            node.add(self.section(_child, _kind, context))
        _columns = element.find("columns")
        _inner = context
        if _columns is not None:
            (_columns_node, _width) = self.columns(_columns, context)
            node.add(_columns_node)
            _inner = context.wide(_width)
        _group = element.find("group")
        if _group is not None:
            node.add(self.group(_group, _inner))
        _detail = element.find("detail")
        if _detail is not None:
            node.add(self.section(_detail, "detail", _inner))

    def inline_bands(self, sections, context):
        """Return the bands of an embedded layout as an inline one has them.

        PythonReports runs an embedded subreport inline, and lets it have
        a page header and footer of its own.  s-reports lets an inline
        subreport have neither, so a header becomes a title and a footer
        a summary, where the layout has none.

        """
        _kinds = dict(sections)
        _rv = []
        for (_kind, _child) in sections:
            if _kind in ("header", "footer"):
                _new = "title" if _kind == "header" else "summary"
                _path = "%s/%s" % (context.path, _kind)
                if _new in _kinds:
                    self.note(_path, "an inline subreport has no %s "
                        "in s-reports, and the layout has a %s already: "
                        "the %s is left out" % (_kind, _new, _kind))
                    continue
                self.note(_path, "an inline subreport has no %s in s-reports: "
                    "the %s became a %s, which prints once" % (_kind, _kind,
                    _new))
                _kinds[_new] = _child
                _rv.append((_new, _child))
            else:
                _rv.append((_kind, _child))
        return _rv

    def columns(self, element, context):
        """Return the columns node, and the width of a column."""
        _node = kdl.Node("columns")
        _node.blank = True
        _count = int(datatypes.Integer(element.get("count")))
        _node.set("count", _count)
        _gap = element.get("gap")
        _gap_points = _points(_gap) if _gap else 0
        if _gap and _gap_points:
            _node.set("gap", _dimension(_gap))
        _width = None
        if context.width is not None:
            _width = (context.width - (_count - 1) * _gap_points) / _count
        _inner = context.child("columns", element, _width)
        _node.children.extend(self.styles(element, _inner))
        for _kind in ("header", "footer"):
            _child = element.find(_kind)
            if _child is not None:
                _node.add(self.section(_child, _kind, _inner))
        return (_node, _width)

    def group(self, element, context):
        """Return the node of a group element."""
        _name = element.get("name")
        _path = "%s/group[%s]" % (context.path, _name)
        _node = kdl.Node("group", _name)
        _node.blank = True
        _node.set("expr", self.expr_text(_path, element.get("expr"), _node))
        _context = context.child("group[%s]" % _name, element)
        _node.children.extend(self.styles(element, _context))
        self.nesting(element, _node, _context)
        return _node

    # -- styles ----------------------------------------------------------

    def styles(self, element, context):
        """Return the style nodes of an element."""
        return self.style_nodes(element.findall("style"), context)

    def style_nodes(self, styles, context):
        """Return the style nodes of a sequence of style elements.

        The printwhen of each style is left out: s-reports keeps it on the
        element or section, and `printwhen` collects it there.

        """
        _rv = []
        for _style in styles:
            _node = kdl.Node("style")
            _when = _style.get("when")
            if not _is_true(_when):
                _node.set("when", self.expr_text(context.path,
                    _when, _node, hint="nullable"))
            if _style.get("font"):
                _node.set("font", _style.get("font").strip())
            for _name in ("color", "bgcolor"):
                if _style.get(_name) and _style.get(_name).strip():
                    _node.set(_name, _color(_style.get(_name)))
            if any(_node.has(_name) for _name in ("font", "color", "bgcolor")):
                _rv.append(_node)
        return _rv

    def printwhen(self, styles, path, node):
        """Return the printwhen expression a sequence of styles makes.

        PythonReports takes the printwhen of the first style whose
        "when" is true and that has a printwhen.

        Parameters:
            styles: style elements, in the order they are searched.
            path: where the result goes, for notes.
            node: the node that gets the result, for notes.

        Return value: expression text, or None if nothing is suppressed.

        """
        _chain = []
        for _style in styles:
            _printwhen = _style.get("printwhen")
            if not (_printwhen and _printwhen.strip()):
                continue
            _when = _style.get("when")
            # A record field tested for truth may well be null.
            _chain.append((None if _is_true(_when)
                else self.expression(path, _when, node, hint="nullable"),
                self.expression(path, _printwhen, node, hint="nullable")))
            if _is_true(_when):
                break
        if not _chain:
            return None
        if all(_item.tree is not None for _pair in _chain for _item in _pair
            if _item is not None
        ):
            _tree = None
            for (_when, _printwhen) in reversed(_chain):
                if _when is None:
                    _tree = _printwhen.tree
                else:
                    _tree = ast.IfExp(test=_when.tree, body=_printwhen.tree,
                        orelse=_tree or ast.Constant(value=True))
            return starlark(_tree)
        _text = "True"
        for (_when, _printwhen) in reversed(_chain):
            if _when is None:
                _text = "(%s)" % _printwhen.text
            else:
                _text = "(%s) if (%s) else (%s)" % (_printwhen.text,
                    _when.text, _text)
        return _text

    # -- sections --------------------------------------------------------

    def section(self, element, kind, context):
        """Return the node of a section element."""
        _path = "%s/%s" % (context.path, kind)
        _node = kdl.Node(kind)
        _node.blank = True
        _box = element.find("box")
        _declared = 0
        if _box is not None:
            _height = _box.get("height")
            if _height and (_points(_height) > 0):
                _node.set("height", _dimension(_height))
                _declared = _points(_height)
            _ignored = [_name for _name in ("x", "y", "width", "float",
                "halign", "valign") if _box.get(_name)]
            if _ignored:
                self.note(_path, "s-reports sections have no %s: left out"
                    % ", ".join(_ignored), _node)
        _section = context.section(kind, element)
        _minimum = self.band_minimum(element, _declared, _section)
        if _minimum > _declared:
            _node.set("height", _rounded(_minimum))
            self.note(_path, "PythonReports makes this band %s pt tall at "
                "least, for the elements placed from its bottom edge, and "
                "s-reports would not" % kdl.number(_rounded(_minimum)), _node)
        for _name in ("swapheader", "swapfooter"):
            if element.get(_name) and _boolean(element.get(_name)):
                _node.set(_name, True)
        _printwhen = self.printwhen(context.section_styles(element, kind),
            _path, _node)
        if _printwhen:
            _node.set("printwhen", _printwhen)
        _node.children.extend(self.styles(element, _section))
        for _child in element.findall("eject"):
            _node.add(self.eject(_child, _path))
        _outlines = element.findall("outline")
        if len(_outlines) > 1:
            self.note(_path, "PythonReports makes an entry for every outline "
                "whose \"when\" is true, and s-reports for the first of them",
                _node)
        for _child in _outlines:
            _node.add(self.outline(_child, _path))
        _counts = {}
        for _child in element:
            if (_child.tag in BODY) or (_child.tag == "xref"):
                _counts[_child.tag] = _counts.get(_child.tag, 0) + 1
                _child_path = "%s/%s[%i]" % (_path, _child.tag,
                    _counts[_child.tag])
                _node.add(self.element(_child, _section, _child_path))
        _subreports = element.findall("subreport")
        if _subreports and not ((kind == "detail")
            or ((kind == "title") and not _node.get("swapheader"))
            or ((kind == "summary") and not _node.get("swapfooter"))
        ):
            self.note(_path, "s-reports runs subreports only from a detail, "
                "a title without swapheader, or a summary without "
                "swapfooter", _node)
        for _child in _subreports:
            _node.add(self.subreport(_child, _path))
        return _node

    def band_minimum(self, element, declared, context):
        """Return the least height PythonReports gives a band that grows.

        A band grows when it declares no height, or holds something
        that grows: a stretch field, a growing image, or a bar code.
        It is then as tall as its elements reach, and PythonReports
        counts an element placed from the bottom edge as reaching
        1 + its distance from that edge, or its height if that is more.
        s-reports counts no such element, since its place comes from
        the band.

        """
        _elements = [_child for _child in element
            if (_child.tag in BODY) or (_child.tag == "xref")]
        _grows = (declared <= 0) or any(
            ((_child.tag == "field") and _child.get("stretch")
                and _boolean(_child.get("stretch")))
            or ((_child.tag == "image")
                and ((_child.get("scale") or "").strip() == "grow"))
            or (_child.tag == "barcode")
            for _child in _elements)
        if not _grows:
            return 0
        _rv = 0
        # How far the elements s-reports measures reach, at least.
        _reach = declared
        for _child in _elements:
            _box = _child.find("box")
            _ypos = _points(_box.get("y") or "0") if _box is not None else 0
            _height = _points(_box.get("height") or "-1") \
                if _box is not None else -1
            if (_ypos >= 0) and (_height >= 0):
                _reach = max(_reach, _ypos + _height)
                continue
            if (_child.tag == "xref") and (_height < 0) and (_ypos >= 0) \
            and self.xref_height(_child):
                _reach = max(_reach, _ypos + self.xref_height(_child))
                continue
            if (_child.tag == "image") and (_height < 0) \
            and ((_child.get("scale") or "").strip() == "grow"):
                continue
            # A stretch field and a bar code are sized by their content,
            # which is a line of text or a quarter of an inch at least.
            if _child.tag == "barcode":
                _reach = max(_reach, max(_ypos, 0) + 18)
                continue
            if (_child.tag == "field") and _child.get("stretch") \
            and _boolean(_child.get("stretch")):
                _reach = max(_reach, max(_ypos, 0)
                    + (context.font_size(_child) or 1))
                continue
            if _ypos < 0:
                _rv = max(_rv, 1 - _ypos, _height)
            elif _height < 0:
                _rv = max(_rv, _ypos + 1 - _height)
        return _rv if _rv > _reach + 0.0005 else 0

    def eject(self, element, path):
        """Return the node of an eject element."""
        _node = kdl.Node("eject")
        _type = (element.get("type") or "page").strip()
        if _type != "page":
            _node.set("type", _type)
        if element.get("when") and not _is_true(element.get("when")):
            _node.set("when", self.expr_text(path, element.get("when"),
                _node))
        if element.get("require"):
            _node.set("require", _dimension(element.get("require")))
        return _node

    def outline(self, element, path):
        """Return the node of an outline element."""
        _node = kdl.Node("outline")
        _node.set("title", self.expr_text(path, element.get("title"), _node))
        _level = element.get("level")
        if _level and (int(datatypes.Integer(_level)) != 1):
            _node.set("level", int(datatypes.Integer(_level)))
        for _name in ("name", "when"):
            if element.get(_name) and element.get(_name).strip():
                _result = self.expression(path, element.get(_name), _node)
                _node.set(_name, _result.text)
                if (_name == "name") and isinstance(_result.tree,
                    ast.Constant
                ):
                    self.outline_names.add(str(_result.tree.value))
        if element.get("closed") and _boolean(element.get("closed")):
            _node.set("closed", True)
        return _node

    def subreport(self, element, path):
        """Return the node of a subreport element."""
        _node = kdl.Node("subreport")
        _node.set("seq", int(datatypes.Integer(element.get("seq"))))
        _template = element.get("template")
        _embedded = element.get("embedded")
        if _template:
            _template = _template.strip()
            (_stem, _ext) = os.path.splitext(_template)
            _target = (_stem if _ext.lower() in SOURCE_EXTENSIONS
                else _template) + EXTENSION
            _node.set("template", _target)
            if (_template, _target) not in self.subreports:
                self.subreports.append((_template, _target))
            self.note(path, "convert the subreport template %s to %s as well"
                % (_template, _target), _node)
        else:
            _node.set("embedded", _embedded.strip())
        _data = element.get("data")
        _node.set("data", self.expr_text(path, _data, _node, hint="list"))
        if element.get("when") and not _is_true(element.get("when")):
            _node.set("when", self.expr_text(path, element.get("when"),
                _node))
        _inline = bool(element.get("inline")) \
            and _boolean(element.get("inline"))
        _ownpageno = bool(element.get("ownpageno")) \
            and _boolean(element.get("ownpageno"))
        if _embedded:
            # PythonReports runs every embedded subreport inline.
            _inline = True
            if _ownpageno:
                self.note(path, "an inline subreport cannot number its own "
                    "pages: ownpageno is left out", _node)
                _ownpageno = False
        if _inline:
            _node.set("inline", True)
            if _template:
                self.check_inline(_template, path, _node)
        if _ownpageno:
            _node.set("ownpageno", True)
        for _arg in element.findall("arg"):
            _arg_node = _node.add(kdl.Node("arg", _arg.get("name")))
            _arg_node.set("value", self.expr_text(path, _arg.get("value"),
                _node))
        return _node

    def check_inline(self, template, path, node):
        """Note an inline subreport whose template s-reports would refuse.

        PythonReports lets an inline subreport have a page header and
        footer of its own; s-reports does not.

        """
        _file = os.path.join(os.path.dirname(os.path.abspath(self.path)),
            self.basedir or "", template)
        try:
            _layout = load_raw(_file).find("layout")
        except Exception:
            return
        _bands = [_kind for _kind in ("header", "footer")
            if _layout.find(_kind) is not None]
        if _bands:
            self.note(path, "%s has a page %s, and s-reports refuses one in "
                "a subreport that runs inline: take the %s out of the "
                "converted template, or run the subreport on pages of "
                "its own" % (template, " and ".join(_bands),
                    " and ".join(_bands)), node)

    # -- body elements ---------------------------------------------------

    def element(self, element, context, path, inherited=()):
        """Return the node of a body element or an xref.

        Parameters:
            element: the template element.
            context: the context of the container.
            path: where the element is, for notes.
            inherited: style elements of an xref holding the element,
                which s-reports cannot keep on the xref.

        """
        _node = kdl.Node(element.tag)
        _styles = element.findall("style") + list(inherited)
        # What the element shows comes first, then where it goes.
        _placed = kdl.Node(element.tag)
        _width = self.geometry(element, _placed, _node, context, path)
        _converter = getattr(self, "element_" + element.tag)
        _converter(element, _node, context, path, _width)
        if element.tag == "field":
            self.field_height(element, _placed, _node, context, path)
        _node.props.extend(_placed.props)
        if element.tag != "xref":
            _printwhen = self.element_printwhen(element,
                inherited, _node, path)
            if _printwhen:
                _node.set("printwhen", _printwhen)
            _node.children.extend(self.style_nodes(_styles, context))
        return _node

    def element_printwhen(self, element, inherited, node, path):
        """Return the printwhen of a body element, or None.

        PythonReports hides an xref, and all it holds, by the printwhen
        of the xref's styles, and an element inside it by the printwhen
        of the element's own.  s-reports has no printwhen on an xref,
        so an element inside one prints where both conditions hold.
        The xref's comes first, since PythonReports tests it first.

        Parameters:
            element: the template element.
            inherited: style elements of an xref holding the element.
            node: the node of the element, for notes.
            path: where the element is, for notes.

        """
        _parts = [_text for _text in (
            self.printwhen(list(inherited), path, node),
            self.printwhen(element.findall("style"), path, node)) if _text]
        _guard = self.none_guard(element, node, path)
        if (len(_parts) > 1) or (_parts and _guard):
            _parts = ["(%s)" % _text for _text in _parts]
        if _guard:
            _parts.append(_guard)
        return " and ".join(_parts) or None

    def none_guard(self, element, node, path):
        """Return a printwhen that keeps a field from printing None.

        PythonReports prints nothing for a value of None.  s-reports prints
        "None", or refuses a numeric format.  A field that shows a
        variable, the usual way to get a None, prints only when the
        value is not None.

        """
        if (element.tag != "field") or node.has("evaltime"):
            return None
        _source = (element.get("expr") or "").strip()
        _calc = self.scope.calcs.get(_source)
        if (_calc is None) or (_calc in ("count", "list", "set", "chain")):
            return None
        self.note(path, "PythonReports prints nothing for a value of None, "
            "and s-reports prints None: the field prints only when %s is not "
            "None" % _source, node)
        return "%s != None" % node.get("expr")

    def geometry(self, element, node, notes, context, path):
        """Set the position and size properties of a node from its box.

        Parameters:
            element: the template element.
            node: the node that gets the properties.
            notes: the node that gets the notes.
            context: the context of the container.
            path: where the element is, for notes.

        Return value: the width of the element in points, where it is known.

        """
        _box = element.find("box")
        _attrs = {} if _box is None else _box.attrib
        _kind = element.tag
        _container = context.width
        # PythonReports counts a negative position or size from the far
        # edge of the container, plus one: x="-1" is the right edge,
        # and width="-1" reaches it.
        _xpos_text = _attrs.get("x") or "0"
        _width_text = _attrs.get("width") or "-1"
        (_xpos, _width) = (_points(_xpos_text), _points(_width_text))
        if _xpos >= 0:
            _left = _dimension(_xpos_text)
            if _width >= 0:
                (_right, _extent, _known) = (None, _dimension(_width_text),
                    _width)
            else:
                _right = _rounded(-(_width + 1))
                _extent = None
                _known = None if _container is None \
                    else _container - _xpos + _width + 1
        else:
            _left = None
            if _width >= 0:
                (_right, _extent, _known) = (_rounded(-(_xpos + 1) - _width),
                    _dimension(_width_text), _width)
            else:
                _known = max(_width - _xpos, 0)
                (_right, _extent) = (_rounded(-(_width + 1)),
                    _rounded(_known))
        if (_kind in ("line", "rectangle")) and (_extent is not None):
            # A line or a rectangle spends "width" on its stroke,
            # so its extent is given by both edges.
            if _container is None:
                self.note(path, "the width of the container is not known, "
                    "so the extent of this %s is not set: give it left and "
                    "right" % _kind, notes)
            elif _left is None:
                _left = _rounded(_container + 1 + _xpos)
            else:
                _right = _rounded(_container - _xpos - _width)
            _extent = None
        # s-reports fills in a missing edge as zero, left before right,
        # so a box that names its width and counts from the right edge
        # writes that edge even where it is zero.
        if _extent is None:
            if _left:
                node.set("left", _left)
            if _right:
                node.set("right", _right)
        elif _left is not None:
            if _left:
                node.set("left", _left)
            node.set("width", _extent)
        else:
            node.set("right", _right)
            node.set("width", _extent)
        # Vertically: top, bottom and height, the same way.
        _ypos_text = _attrs.get("y") or "0"
        _height_text = _attrs.get("height") or "-1"
        (_ypos, _height) = (_points(_ypos_text), _points(_height_text))
        _content = self.xref_height(element) \
            if (_kind == "xref") and (_height < 0) and (_ypos >= 0) else None
        if _content:
            # PythonReports grows an xref to what it holds, and s-reports
            # sizes one as any other box, so it gets its contents' height.
            _top = _dimension(_ypos_text)
            (_bottom, _tall) = (None, _rounded(_content))
            self.note(path, "PythonReports makes an xref as tall as what "
                "it holds, and s-reports does not: the xref is %s pt "
                "tall, the height of its contents" % kdl.number(_tall),
                notes)
        elif _ypos >= 0:
            _top = _dimension(_ypos_text)
            if _height >= 0:
                (_bottom, _tall) = (None, _dimension(_height_text))
            else:
                (_bottom, _tall) = (_rounded(-(_height + 1)), None)
        else:
            _top = None
            if _height >= 0:
                (_bottom, _tall) = (_rounded(-(_ypos + 1) - _height),
                    _dimension(_height_text))
            else:
                (_bottom, _tall) = (_rounded(-(_height + 1)),
                    _rounded(max(_height - _ypos, 0)))
        if _top:
            node.set("top", _top)
        if _bottom or ((_top is None) and (_bottom is not None)):
            node.set("bottom", _bottom)
        if _tall is not None:
            node.set("height", _tall)
        if _attrs.get("float") and _boolean(_attrs.get("float")):
            if _ypos < 0:
                self.note(path, "PythonReports does not float a box "
                    "placed from the bottom: float is left out", notes)
            elif (_tall is None) and not ((_kind == "field")
                and element.get("stretch") and _boolean(element.get("stretch"))
            ) and (_kind != "barcode") and not ((_kind == "image")
                and (element.get("scale") or "").strip() == "grow"
            ):
                self.note(path, "s-reports floats only an element "
                    "with a height of its own: float is left out", notes)
            else:
                node.set("float", True)
        if _kind in ("field", "image", "barcode", "xref"):
            _halign = (_attrs.get("halign") or "left").strip()
            _valign = (_attrs.get("valign") or "bottom").strip()
            if _kind == "xref":
                pass
            else:
                if _halign != "left":
                    node.set("halign", _halign)
                if _valign != "top":
                    node.set("valign", _valign)
        return _known

    def xref_height(self, element):
        """Return the height of what an xref holds, where boxes say it.

        Only boxes placed from the top with a height of their own
        say where they end; the others are sized by the xref.

        """
        _rv = 0
        for _child in element:
            if _child.tag not in BODY:
                continue
            _box = _child.find("box")
            if _box is None:
                continue
            _ypos = _points(_box.get("y") or "0")
            _height = _points(_box.get("height") or "-1")
            if (_ypos >= 0) and (_height >= 0):
                _rv = max(_rv, _ypos + _height)
        return _rv

    def element_xref(self, element, node, context, path, width):
        """Fill the node of an xref element."""
        node.set("type", element.get("type").strip())
        for _name in ("target", "caption"):
            _source = element.get(_name)
            if not (_source and _source.strip()):
                continue
            _result = self.expression(path, _source, node)
            _text = _result.text
            if not (isinstance(_result.tree, ast.Constant)
                and isinstance(_result.tree.value, str)
            ):
                # s-reports takes a string here and converts nothing.
                _text = "str(%s)" % _text
            elif (_name == "target") and (node.get("type") == "outline"):
                self.outline_targets.append((path, _result.tree.value, node))
            node.set(_name, _text)
        _styles = element.findall("style")
        if any(_style.get("printwhen") for _style in _styles):
            self.note(path, "s-reports has no printwhen on an xref: the "
                "elements inside it got it instead, and the link is there "
                "even where they do not print", node)
        if _styles:
            self.note(path, "s-reports has no styles on an xref: the elements "
                "inside it got them instead", node)
        _inner = context.child("xref", element, width)
        _counts = {}
        for _child in element:
            if _child.tag in BODY:
                _counts[_child.tag] = _counts.get(_child.tag, 0) + 1
                _child_path = "%s/%s[%i]" % (path, _child.tag,
                    _counts[_child.tag])
                node.add(self.element(_child, _inner, _child_path, _styles))

    def content(self, element, node, path, kind):
        """Set the content of a field or a bar code: expr, text, or data."""
        _expr = element.get("expr")
        _data_name = element.get("data")
        _data_child = element.find("data")
        _format = element.get("format") or "%s"
        if _data_child is not None:
            _data_text = _text_of(_data_child)
        elif _data_name and (_data_name in self.datablocks) \
        and not self.datablocks[_data_name].get("expr"):
            _data_text = _text_of(self.datablocks[_data_name])
        else:
            _data_text = None
        _evaltime = (element.get("evaltime") or "").strip()
        # A numeric conversion says what kind of number a field holds.
        _hints = format_hints(_format)
        if _expr and _expr.strip() and _evaltime:
            _result = self.expression(path, _expr, node, deferred=True,
                hint=_hints)
            if not _result.final:
                self.note(path, "the deferred expression %s reads nothing "
                    "that changes as the report is built, so it is "
                    "evaluated in place" % _expr.strip(), node)
                node.set("expr", _result.text)
                self.set_format(node, _format, path)
                return
            node.set("expr", _result.text)
            node.set("evaltime", _evaltime)
            self.set_format(node, _format, path)
            if _data_child is not None:
                node.set("text", _data_text)
            elif _data_name:
                node.set("data", _data_name.strip())
            elif (kind == "barcode") or (element.get("stretch")
                and _boolean(element.get("stretch"))
            ):
                node.set("text", _placeholder(_format))
                self.note(path, "s-reports measures a deferred %s by a "
                    "placeholder, and the template gave none: the one "
                    "written here is a guess, so make it as long as the "
                    "longest value" % kind, node)
            return
        if _expr and _expr.strip():
            _result = self.expression(path, _expr, node, hint=_hints)
            _tree = _result.tree
            if isinstance(_tree, ast.Constant) \
            and isinstance(_tree.value, str) and (_format == "%s"):
                node.set("text", _tree.value)
            else:
                node.set("expr", _result.text)
                self.set_format(node, _format, path)
            return
        if _data_text is not None:
            # PythonReports applies the format to data blocks too.
            if _format != "%s":
                try:
                    _data_text = _format % _data_text
                except (TypeError, ValueError):
                    self.note(path, "the format %s does not apply to the "
                        "text: it is left out" % _format, node)
            node.set("text", _data_text)
            return
        if _data_name:
            node.set("data", _data_name.strip())
            if _format != "%s":
                self.note(path, "PythonReports applies the format %s to the "
                    "data block, and s-reports applies a format to expr only"
                    % _format, node)
            return
        node.set("text", "")

    def set_format(self, node, spec, path):
        """Set the format property of a node from a Python % format."""
        if spec == "%s":
            return
        (_converted, _notes) = engine_format(spec)
        for _message in _notes:
            self.note(path, "format %s: %s" % (spec, _message), node)
        node.set("format", _converted if _converted is not None else spec)

    def element_field(self, element, node, context, path, width):
        """Fill the node of a field element."""
        # pylint: disable=unused-argument
        # The element converters take the same arguments.
        self.content(element, node, path, "field")
        _align = (element.get("align") or "left").strip()
        if _align != "left":
            node.set("align", _align)
        if element.get("stretch") and _boolean(element.get("stretch")):
            node.set("stretch", True)

    def field_height(self, element, placed, node, context, path):
        """Make a fixed field box hold the lines PythonReports set in it.

        PythonReports fits n lines of a font of size s in a box
        (1.2 n - 0.2) s tall, and makes a box hold one line at least.
        s-reports gives every line 1.2 s.

        Parameters:
            element: the field element.
            placed: the node holding the geometry of the field.
            node: the field node, for notes.
            context: the context of the container.
            path: where the field is, for notes.

        """
        if element.get("stretch") and _boolean(element.get("stretch")):
            return
        _box = element.find("box")
        _text = None if _box is None else _box.get("height")
        if not (_text and (_points(_text) >= 0)):
            return
        _height = _points(_text)
        _size = context.font_size(element)
        if _size is None:
            return
        _lines = max(int((_height / _size + 0.2) / 1.2 + 1e-9), 1)
        _needed = round(1.2 * _lines * _size, 3)
        if _needed > _height + 0.0005:
            placed.set("height", _rounded(_needed))
            self.note(path, "the box is %s pt tall to hold %i line%s of "
                "%i pt text, as it did in PythonReports" % (
                    kdl.number(_rounded(_needed)), _lines,
                    "" if _lines == 1 else "s", _size), node)

    def element_line(self, element, node, context, path, width):
        """Fill the node of a line element."""
        # pylint: disable=unused-argument
        # The element converters take the same arguments.
        self.pen(element, node, path, "line")
        # PythonReports draws a sloped line rising, "/", unless told
        # backslant, and s-reports draws it falling, "\", unless told so.
        # A level or upright line is the same either way.
        _box = element.find("box")
        _attrs = {} if _box is None else _box.attrib
        _tall = _span(_points(_attrs.get("y") or "0"),
            _points(_attrs.get("height") or "-1"))
        _flat = (width == 0) or (_tall == 0)
        _backslant = bool(element.get("backslant")) \
            and _boolean(element.get("backslant"))
        if not (_flat or _backslant):
            node.set("backslant", True)

    def element_rectangle(self, element, node, context, path, width):
        """Fill the node of a rectangle element."""
        # pylint: disable=unused-argument
        # The element converters take the same arguments.
        self.pen(element, node, path, "rectangle")
        if element.get("radius") and _points(element.get("radius")):
            node.set("radius", _dimension(element.get("radius")))
        if element.get("opaque") and not _boolean(element.get("opaque")):
            node.set("opaque", False)

    def pen(self, element, node, path, kind):
        """Set the stroke of a line or a rectangle from its pen."""
        _pen = (element.get("pen") or "").strip()
        if _pen in ("dot", "dash", "dashdot"):
            # PythonReports draws a patterned pen one point wide.
            node.set("width", 1)
            node.set("dash", _pen)
        elif _points(_pen) == 0:
            if kind == "rectangle":
                node.set("stroke", False)
            else:
                node.disabled = True
                self.note(path, "a pen 0 line draws nothing, and in s-reports "
                    "a width of 0 is a hairline: the line is commented out",
                    node)
        else:
            node.set("width", _dimension(_pen))

    def element_image(self, element, node, context, path, width):
        """Fill the node of an image element."""
        # pylint: disable=unused-argument
        # The element converters take the same arguments.
        _file = element.get("file")
        _data_name = element.get("data")
        _data_child = element.find("data")
        if _file and _file.strip():
            node.set("file", _file.strip())
            if _data_name or (_data_child is not None):
                self.note(path, "the image names a file and data, "
                    "and s-reports takes one: the data are left out",
                    node)
            if element.get("embed") and not _boolean(element.get("embed")):
                node.set("embed", False)
        elif _data_name and _data_name.strip():
            node.set("data", _data_name.strip())
        elif _data_child is not None:
            _data = _data_bytes(_data_child)
            if isinstance(_data, str):
                _data = _data.encode("latin-1", "replace")
            node.add(kdl.Node("content", kdl.Multiline(
                _base64_lines(_data or b""))))
        _scale = (element.get("scale") or "cut").strip()
        if _scale != "cut":
            node.set("scale", _scale)
        if element.get("proportional") \
        and not _boolean(element.get("proportional")):
            node.set("proportional", False)

    def element_barcode(self, element, node, context, path, width):
        """Fill the node of a bar code element."""
        # pylint: disable=unused-argument
        # The element converters take the same arguments.
        _type = element.get("type").strip()
        node.props.insert(0, ("type", _type))
        self.content(element, node, path, "barcode")
        _module = element.get("module")
        if _module and (float(_module) != 10):
            node.set("module", "%smil" % kdl.number(float(_module)))
        for _name in ("vertical", "grow"):
            if element.get(_name) and _boolean(element.get(_name)):
                node.set(_name, True)
        # PythonReports paints a bar code on a white background.
        node.set("paper", "#FFFFFF")
        if (_type == "2of5i") and node.has("expr"):
            self.note(path, "s-reports refuses an odd number of digits for "
                "2of5i, where PythonReports pads: a format such as %04d "
                "fixes the width", node)

class _Context(object):

    """Where an element is: its path, its ancestors, its container width"""

    def __init__(self, converter, path, ancestors, width, kind=None):
        self.converter = converter
        self.path = path
        # Template elements from the layout down to the container.
        self.ancestors = ancestors
        self.width = width
        self.kind = kind

    def child(self, name, element, width=None):
        """Return the context of an element inside this one."""
        return _Context(self.converter, "%s/%s" % (self.path, name),
            self.ancestors + [element],
            self.width if width is None else width)

    def wide(self, width):
        """Return this context with another container width."""
        return _Context(self.converter, self.path, self.ancestors,
            self.width if width is None else width, self.kind)

    def section(self, kind, element):
        """Return the context of the elements inside a section."""
        _rv = self.child(kind, element)
        _rv.kind = kind
        return _rv

    def section_styles(self, element, kind):
        """Return the styles PythonReports searches for a section.

        The section's own, then those of each container outward.
        Every section but the detail spans the columns of the element
        it belongs to, so the styles of those columns do not apply.

        """
        _rv = list(element.findall("style"))
        _skip = 1 if kind == "detail" else 2
        _chain = [element] + list(reversed(self.ancestors))
        for (_idx, _ancestor) in enumerate(_chain):
            if _idx == 0:
                continue
            if _idx >= _skip:
                _rv.extend(_ancestor.findall("columns/style"))
            _rv.extend(_ancestor.findall("style"))
        return _rv

    def font_size(self, element):
        """Return the largest size the font of an element may have.

        The search is the style search of PythonReports: the element's
        own styles, then those of its containers.  It stops at the first
        style that names a font and applies always.

        """
        _styles = list(element.findall("style"))
        for _ancestor in reversed(self.ancestors):
            _styles.extend(_ancestor.findall("columns/style"))
            _styles.extend(_ancestor.findall("style"))
        _sizes = []
        for _style in _styles:
            _font = _style.get("font")
            if not _font:
                continue
            _definition = self.converter.fonts.get(_font.strip())
            if _definition is None:
                return None
            _sizes.append(int(datatypes.Integer(_definition.get("size"))))
            if _is_true(_style.get("when")):
                return max(_sizes)
        return None

# vim: set et sts=4 sw=4 :
