"""A KDL v2 writer for converted templates.

s-reports templates are KDL v2 documents.  The converter builds a tree
of `Node` objects and `dumps` writes it out the way a person would:
one node per line, properties after the arguments, long nodes broken
with line continuations, and comments placed above the node they
describe.

Only writing is needed here.  Reading KDL is the business of s-reports,
which the tests use to check what this module writes.

"""

__all__ = ["Multiline", "Node", "dumps", "number", "quote", "spelled"]

import re

# Lines are kept under this width wherever a single token allows it.
WIDTH = 79

# Characters KDL v2 does not allow in a document as they stand:
# control characters other than the whitespace it knows,
# the newline characters (a single-line string holds none),
# the bidirectional controls, and the byte order mark.
_ESCAPED = re.compile("[\x00-\x1f\x7f\x85\u200e\u200f\u2028\u2029"
    "\u202a-\u202e\u2066-\u2069\ufeff\ud800-\udfff]")

_SHORT_ESCAPES = {
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}

# A string that can be written without quotes would still be quoted:
# a bare identifier reads as a string in KDL v2, but a reader of the
# template should not have to know that.  Only names are written bare.
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")

class Multiline(str):

    """A string written as a triple-quoted block

    Used for long blobs such as base64 content.  The text must not
    contain backslashes, quotes, or characters that need escaping;
    each of its lines is indented to the block.

    """

class Node(object):

    """One KDL node: a name, arguments, properties, and children

    Attributes:
        name: the node name.
        args: positional arguments, in order.
        props: list of (name, value) pairs, in order.
        children: child nodes, in order.
        comments: comment lines written above the node.
        disabled: True to write the node commented out with "/-".
        blank: True to separate the node from the one before it
            with an empty line.

    """

    def __init__(self, name, *args):
        """Create a node with optional positional arguments.

        Parameters:
            name: the node name.
            args: positional argument values.

        """
        self.name = name
        self.args = list(args)
        self.props = []
        self.children = []
        self.comments = []
        self.disabled = False
        self.blank = False

    def set(self, name, value):
        """Set a property, replacing an earlier value of the same name.

        A replaced value keeps its place.
        A value of None removes the property.

        """
        for (_idx, _item) in enumerate(self.props):
            if _item[0] == name:
                if value is None:
                    del self.props[_idx]
                else:
                    self.props[_idx] = (name, value)
                return self
        if value is not None:
            self.props.append((name, value))
        return self

    def get(self, name, default=None):
        """Return the value of a property, or default if it is not set."""
        for (_name, _value) in self.props:
            if _name == name:
                return _value
        return default

    def has(self, name):
        """Return True if the node has a property of this name."""
        return any(_item[0] == name for _item in self.props)

    def add(self, child):
        """Append a child node and return it."""
        self.children.append(child)
        return child

    def note(self, text):
        """Add a comment line above the node."""
        self.comments.append(text)
        return self

    def find(self, name):
        """Return the first child with this name, or None."""
        for _child in self.children:
            if _child.name == name:
                return _child
        return None

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.name)

def number(value):
    """Return the KDL spelling of a number.

    Integral values carry no fractional part, and there is never
    an exponent, so that the template reads the way it was written.

    """
    if isinstance(value, bool):
        raise TypeError("a boolean is not a number")
    if isinstance(value, int):
        return str(value)
    if value == int(value):
        return str(int(value))
    _text = "%.6f" % value
    return _text.rstrip("0").rstrip(".")

def quote(text):
    """Return a string as a KDL v2 string literal.

    A string holding backslashes and nothing that needs an escape
    is written raw, so that an expression reads as Starlark spells it.
    Everything else is written quoted, with escapes.

    """
    if ("\\" in text) and not _ESCAPED.search(text):
        _hashes = "#"
        while "\"" + _hashes in text:
            _hashes += "#"
        return "%s\"%s\"%s" % (_hashes, text, _hashes)
    _text = text.replace("\\", "\\\\").replace("\"", "\\\"")
    return "\"%s\"" % _ESCAPED.sub(_escape, _text)

def _escape(match):
    """Return the KDL escape for one character."""
    _char = match.group(0)
    try:
        return _SHORT_ESCAPES[_char]
    except KeyError:
        return "\\u{%x}" % ord(_char)

def spelled(item):
    """Return the KDL spelling of an argument or property value."""
    if item is None:
        return "#null"
    if isinstance(item, bool):
        return "#true" if item else "#false"
    if isinstance(item, (int, float)):
        return number(item)
    return quote(str(item))

def _identifier(text):
    """Return a node or property name, quoted where it has to be."""
    if _IDENTIFIER.match(text):
        return text
    return quote(text)

def _comment(text, indent):
    """Return comment lines wrapped to the page width."""
    _width = max(WIDTH - len(indent) - 3, 20)
    _rv = []
    for _paragraph in text.split("\n"):
        _line = ""
        for _word in _paragraph.split():
            if _line and (len(_line) + 1 + len(_word) > _width):
                _rv.append(_line)
                _line = _word
            else:
                _line = ("%s %s" % (_line, _word)) if _line else _word
        _rv.append(_line)
    return ["%s// %s" % (indent, _line) if _line else indent + "//"
        for _line in _rv]

def _multiline(text, indent):
    """Return a triple-quoted block indented to the given level."""
    _inner = indent + "  "
    _rv = ["\"\"\""]
    _rv.extend(_inner + _line for _line in text.split("\n"))
    _rv.append(_inner + "\"\"\"")
    return "\n".join(_rv)

def _tokens(node, indent):
    """Return the tokens of a node's line: name, arguments, properties."""
    _rv = []
    for _arg in node.args:
        if isinstance(_arg, Multiline):
            _rv.append(_multiline(_arg, indent))
        else:
            _rv.append(spelled(_arg))
    for (_key, _value) in node.props:
        _rv.append("%s=%s" % (_identifier(_key), spelled(_value)))
    return _rv

def _lines(node, indent, first=False):
    """Return the lines a node and its children are written as.

    Parameters:
        node: the node.
        indent: the indentation of the node.
        first: True if the node opens a block, where no blank line
            goes before it.

    """
    _rv = []
    if node.blank and not first:
        _rv.append("")
    for _text in node.comments:
        _rv.extend(_comment(_text, indent))
    _head = ("/-" if node.disabled else "") + _identifier(node.name)
    _tokens_list = _tokens(node, indent)
    _opener = " {" if node.children else ""
    _single = " ".join([_head] + _tokens_list) + _opener
    if (len(indent) + len(_single) <= WIDTH) or ("\n" in _single):
        _rv.append(indent + _single)
    else:
        # Break the line, aligning continuations after the node name.
        # The first token stays beside the name however long it is,
        # and room is kept for the " \" that continues a line.
        _hang = indent + " " * (len(_head) + 1)
        _line = indent + _head
        for (_idx, _token) in enumerate(_tokens_list):
            _candidate = _line + " " + _token
            if (_idx == 0) or (len(_candidate) + 2 <= WIDTH):
                _line = _candidate
            else:
                _rv.append(_line + " \\")
                _line = _hang + _token
        _rv.append(_line + _opener)
    if node.children:
        for (_idx, _child) in enumerate(node.children):
            _rv.extend(_lines(_child, indent + "  ", _idx == 0))
        _rv.append(indent + "}")
    return _rv

def dumps(nodes, comments=()):
    """Return a KDL document holding the given top-level nodes.

    Parameters:
        nodes: sequence of Node objects.
        comments: comment lines written at the top of the document.

    """
    _rv = []
    for _text in comments:
        _rv.extend(_comment(_text, ""))
    if comments:
        _rv.append("")
    for (_idx, _node) in enumerate(nodes):
        _rv.extend(_lines(_node, "", _idx == 0))
    return "\n".join(_rv) + "\n"

# vim: set et sts=4 sw=4 :
