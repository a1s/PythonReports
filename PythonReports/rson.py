"""Load a template or printout tree from an RSON file

The RSON syntax is a mix between JSON and YAML.
Compared to JSON, RSON uses relaxed string quoting,
allows comments, and allows Python-style indentation
to create structures.

This module uses the "light" dialect of RSON which drops
compatibility with JSON to make the syntax really simple.

@see: https://pypi.python.org/pypi/rsonlite

This module implements two additions to the basic RSON Lite syntax:

    1. Quoted strings.  When a value starts and ends with a double quote,
       it is passed to Python "eval()".  This allows to insert leading
       and trailing blanks and backslash-escapes.

    2. Short cut one-line notation for simple structures.
       When a value starts with open square bracket and
       ends with closing square bracket, it is parsed as
       a semicol-delimited sequence of simple name=value pairs.
       For example::

        box = [ x = 2 ; y = 3 ; width = 10 ]

       NOTE: One-liners do not support quoted strings, embedded
       structures, and semicols in the keys or values.

The mapping from RSON to traditional XML structures is this:

    - Each key/value pair makes an attribute if the value is a
      simple string, or a child element if this value consists
      of (name, value) tuples.

      Note that RSON Lite yields simple strings as 1-item lists.

    - The root element ("report" for templates and "printout"
      for printouts) is implicit, not serialized (but the root
      attributes may appear in RSON along with root children).

    - After building an XML element, look for attribute named "body".
      When containing element tag is "data", move the value to element text.
      For all other element names, create "data" sub-element.

      Note: Two elements have an attribute named "value":
      "arg" in templates - for passing parameters to subreports, -
      and "barcode" in printouts.  Printout structures have an
      element named "text" .  As of 29-mar-2017, there is nothing
      named "contents", but I'd rather leave that name for TOC.

Implementation of reverse mapping - XML to RSON - is not planned:
RSON is meant to be read and written by humans, there is no need
to store computer-generated structures in that format.

"""

import re
import sys
from warnings import warn

import rsonlite

from PythonReports import datatypes, template

def str2value(txt):
    """Build an output value from an RSON string

    If "txt" is enclosed in square brackets, parse one-line
    short-cut notation and make a list of 2-element tuples.

    Otherwise if "txt" is enclosed in double quotes,
    pass it to Python "eval()" and use the result.

    Otherwise use "txt" as is.

    Decode all values from UTF-8 (that's encoding forced by rsonlite).

    """
    if len(txt) < 2:
        _rv = txt
    elif (txt[0] == "[") and (txt[-1] == "]"):
        _rv = []
        for _item in txt[1:-1].split(";"):
            (_name, _value) = _item.split("=", 1)
            _rv.append((_name.strip(), [str2value(_value.strip())]))
    elif txt[0] == txt[-1] == "\"":
        _rv = eval(txt)
    else:
        _rv = txt
    if not isinstance(_rv, (unicode, list)): # list may come from one-liner
        _rv = _rv.decode("utf-8")
    return _rv

def rson2element(tag, data):
    """Convert an RSON parsing result to a tree of ElementTree Element objects

    RSON output is a sequence of items where each item may be
    either a simple string or a 2-element tuple of string and sequence.

    For the purpose of this module we do not allow to mix these
    two types in the same sequence - i.e. a data sequence may be
    either a list of (name, value) tuples, or a 1-element list
    containing simple string.

    Simple strings make attributes.  Lists of tuples make child elements.

    The "data" argument must be a list of tuples.

    """
    _attrs = {}
    _children = []
    for _item in data:
        if not isinstance(_item, tuple) or (len(_item) != 2):
            # For top level elements without value
            # RSONlite yields RsonToken instead of tuple
            if isinstance(_item, tuple):
                _item = _item[0]
            warn("Unexpected element \"%s\" in RSON input line %s"
                % (_item, _item.line))
            continue
        (_key, _value) = _item
        if not _value: # Skip empties
            continue
        try:
            # _key is RsonToken which does not like to be combined
            # with Unicode values in error messages.
            _name = _key.decode("utf-8")
            if isinstance(_value[0], basestring):
                assert len(_value) == 1
                _value = str2value(_value[0])
            if isinstance(_value, basestring):
                _attrs[_name] = _value
            else:
                _children.append((_name, _value))
        except Exception:
            (_type, _val, _tb) = sys.exc_info()
            raise (ValueError("Failed to parse RSON input in line %s: %s"
                % (_key.line, unicode(_val))), None, _tb)
    _body = _attrs.pop("body", None)
    _rv = datatypes.Element(tag, _attrs)
    for (_name, _value) in _children:
        if _name == "data":
            # Overrides data block defined in parent, if any.
            _body = None
        _rv.append(rson2element(_name, _value))
    if _body is not None:
        if tag == "data":
            _rv.text = _body
        else:
            _sub = datatypes.Element("data")
            _sub.text = _body
            _rv.append(_sub)
    return _rv

def parse_string(txt, validator=template.Report):
    """Build an validate an XML tree from RSON text string"""
    if isinstance(txt, unicode):
        # RSONlite is going to decode it anyway.
        # Do it ourselves in order to detect and remove BOM.
        txt = txt.encode("utf-8")
    # XXX rsonlite does not tolerate BOM:
    # when the first line is empty, BOM appears as a token by itself;
    # otherwise it is added to the element name in the first line.
    if txt.startswith("\xEF\xBB\xBF"):
        txt = txt[3:]
    elif txt.startswith("\xFF\xFE"):
        txt = txt[2:].decode("utf-16-le").encode("utf-8")
    elif txt.startswith("\xFE\xFF"):
        txt = txt[2:].decode("utf-16-be").encode("utf-8")
    _root = rson2element(validator.tag, rsonlite.loads(txt))
    _rv = datatypes.ElementTree(validator, _root)
    _rv.validate()
    return _rv

def parse_file(path, validator=template.Report):
    """Build an validate an XML tree from RSON text file"""
    with open(path, "rU") as _ff:
        _txt = _ff.read()
    _rv = parse_string(_txt, validator=validator)
    _rv.filename = path
    return _rv

_re_nonempty_line = re.compile(r"(?:\xEF\xBB\xBF|\xFF\xFE|\xFE\xFF)?\s*(\S)")

def load_template_file(filename):
    """Load Template file in XML or RSON format, return Template ElementTree

    @param filename: input file path

    Read the beginning of the file until a non-blank character is found.
    When the first non-blank character is the angle bracket ("<"),
    use XML loader.  Otherwise use RSON loader.

    """
    with open(filename, "rU") as _ff:
        for _line in _ff:
            _match = _re_nonempty_line.match(_line)
            if _match:
                if _match.group(1) == "<":
                    _ff.seek(0)
                    _rv = template.load(_ff)
                    _rv.filename = filename
                    return _rv
                break
    # Must be RSON
    return parse_file(filename)

# vim: set et sts=4 sw=4 :
