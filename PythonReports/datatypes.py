"""Data types and element primitives, common for templates and printouts"""

import binascii
import bz2
import cPickle as pickle
import sys
import zlib

from cStringIO import StringIO
from xml.sax import saxutils

# Find ElementTree implementation
# Note: lxml.etree cannot be used because it doesn't allow
# attribute values to be anything but basestrings
# and we need dimensions to act like integers.
try:
    # preferred to pure python because it's faster
    import cElementTree as ET
except ImportError:
    try:
        # preferred to batteries just because you bothered to install it
        import elementtree.ElementTree as ET
    except ImportError:
        # pylint: disable-msg=E0611
        # E0611: No name 'etree' in module 'xml' - true for python <2.5
        # ... pylint still reports this error
        # last resort; should always success in python2.5 and newer
        import xml.etree.ElementTree as ET

# export element factories from ElementTree
Element = ET.Element
SubElement = ET.SubElement

# Fix xml Element function for listing all children.
# Since Python 2.7 Element.getchildren() is deprecated and raises
# DeprecationWarning on use.
if sys.version_info <= (2, 7):
    def getchildren(item):
        return item.getchildren()
else:
    def getchildren(item):
        return list(item)

# XXX This is not the best place for such function.
# It's more about report templates, but the template module
# does not seem proper, either.
def element_label(element):
    """Return string label for an element reference"""
    _rv = _tag = element.tag
    _name = element.get("name", "")
    if _name:
        _rv += " '%s'" % _name
    elif _tag in ("field", "barcode"):
        _expr = element.get("expr", "")
        if not _expr:
            _data = element.find("data")
            if (_data is not None) \
            and not _data.get("pickle", "") \
            and not _data.get("compress", "") \
            and not _data.get("encoding", ""):
                _expr = _data.text
        if _expr:
            if "'" in _expr:
                _quote = "\""
            else:
                _quote = "'"
            _rv += " %s%s%s" % (_quote,
                _expr.replace(_quote, "\\" + _quote), _quote)
    elif _tag == "import":
        _rv += " %s" % element.get("path", "")
    elif _tag == "style":
        _attrs = [_rv]
        _font = element.get("font", "")
        if _font:
            _attrs.append(_font)
        _fg = element.get("color", "")
        _bg = element.get("bgcolor", "")
        if _fg or _bg:
            _attrs.append("%s/%s" % (_fg, _bg))
        _when = element.get("printwhen", "")
        if _when:
            _attrs.append("(%s)" % _when)
        _rv = " ".join(_attrs)
    elif _tag == "subreport":
        _rv += " %s" % element.get("template", "")
    return _rv

### Exceptions

class XmlValidationWarning(UserWarning):

    """Base class for warnings issued by XML element validators"""

    # FIXME: class code is identical for XmlValidationWarning
    # and XmlValidationError.  Needs refactoring.

    # encoding used for string representation of the warning
    encoding = "utf-8"

    def __init__(self, message, element=None, path=None):
        """Create exception

        Parameters:
            message: error message
            element: XML tree element causing the exception
            path: element path in the tree

        """
        UserWarning.__init__(self, message)
        self.message = message
        self.path = path
        self.element = element

    def __unicode__(self):
        _rv = self.message
        if self.path:
            _rv += " in " + self.path
        elif self.element is not None:
            _rv += " for element '%s'" % self.element.tag
        return _rv

    def __str__(self):
        return unicode(self).encode(self.encoding)

class InvalidLiteral(ValueError):

    """Value is rejected by an attribute datatype"""

    def __init__(self, datatype, value):
        """Exception constructor

        Parameters:
            datatype: one of the _Value subclasses
            value: literal that raised the exception

        """
        ValueError.__init__(self, datatype, value)
        self.datatype = datatype
        self.value = value

    def __str__(self):
        return "Invalid literal for %s: %r" % (
            self.datatype.__name__, self.value)

    __unicode__ = __str__

class XmlValidationError(RuntimeError):

    """Base class for errors raised by XML element validators"""

    # encoding used for string representation of the exception
    encoding = "utf-8"

    def __init__(self, message, element=None, path=None):
        """Create exception

        Parameters:
            message: error message
            element: XML tree element causing the exception
            path: element path in the tree

        """
        RuntimeError.__init__(self, message)
        self.message = message
        self.path = path
        self.element = element

    def __unicode__(self):
        _rv = self.message
        if self.path:
            _rv += " in " + self.path
        elif self.element is not None:
            _rv += " for element '%s'" % self.element.tag
        return _rv

    def __str__(self):
        return unicode(self).encode(self.encoding)

class MissingRequiredAttribute(XmlValidationError):

    """Required element attribute is missing"""

    def __init__(self, attribute, element=None, path=None):
        """Exception constructor

        Parameters:
            attribute: attribute name
            element: XML tree element causing the exception
            path: element path in the tree

        """
        XmlValidationError.__init__(self,
            "Required attribute '%s' is missing" % attribute,
            element=element, path=path)
        self.attribute = attribute

class AttributeConversionError(XmlValidationError):

    """Attribute value cannot be converted to required type"""

    def __init__(self, attribute, value, exception=None,
        element=None, path=None
    ):
        """Exception constructor

        Parameters:
            attribute: attribute name
            value: attribute value read from XML source
            exception: exception that was caught during attribute conversion
            element: XML tree element causing the exception
            path: element path in the tree

        """
        XmlValidationError.__init__(self,
            "Invalid value %r for attribute '%s'" % (value, attribute),
            element=element, path=path)
        self.attribute = attribute
        self.value = value
        self.exception = exception

    def __unicode__(self):
        _rv = XmlValidationError.__unicode__(self)
        if self.exception:
            _rv += u" (%s: %s)" % (
                self.exception.__class__.__name__, self.exception)
        return _rv

class MissingRequiredChild(XmlValidationError):

    """Required child element is missing"""

    def __init__(self, childtag, element=None, path=None):
        """Exception constructor

        Parameters:
            childtag: tag name of the missing child element
            element: XML tree element causing the exception
            path: element path in the tree

        """
        XmlValidationError.__init__(self,
            "Required child element '%s' is missing" % childtag,
            element=element, path=path)
        self.childtag = childtag

class ChildMustBeOne(XmlValidationError):

    """There are multiple children of same type but only one is allowed"""

    def __init__(self, childtag, element=None, path=None):
        """Exception constructor

        Parameters:
            childtag: tag name of the missing child element
            element: XML tree element causing the exception
            path: element path in the tree

        """
        XmlValidationError.__init__(self,
            "Only one child of type '%s' is allowed" % childtag,
            element=element, path=path)
        self.childtag = childtag

class DuplicateElement(XmlValidationError):

    """Duplicate name detected in an elements collection"""

    def __init__(self, name, collection, element=None, path=None):
        """Exception constructor

        Parameters:
            name: the name of the element being added
            collection: name of the elements collection
            childtag: tag name of the missing child element
            element: XML tree element causing the exception
            path: element path in the tree

        """
        XmlValidationError.__init__(self,
            "Duplicate name '%s' in %s" % (name, collection),
            element=element, path=path)

class MissingContextError(XmlValidationError):

    """Context not provided for expression evaluation"""

    def __init__(self, expr, element=None, path=None):
        """Exception constructor

        Parameters:
            expr: expression being evaluated
            element: XML tree element causing the exception
            path: element path in the tree

        """
        XmlValidationError.__init__(self,
            "Context not provided for data expression '%s'" % (expr),
            element=element, path=path)

class REQUIRED(object):

    """"Value is required" value

    The singleton instance of this class is a special value
    used instead of default in attribute declarations
    to indicate that the attribute is required.

    """
    # pylint: disable-msg=R0903
    # R0903: Too few public methods

# XXX should NOTHING be different from REQUIRED?
REQUIRED = NOTHING = REQUIRED()

class Structure(object):

    """Simple object with custom attributes

    Structures are silly containers that do nothing but
    hold a set of values.  Attributes may be initialized
    by passing keyword arguments to object constructor.

    """
    # pylint: disable-msg=R0903
    # R0903: Too few public methods

    def __init__(self, **kwargs):
        for (_name, _value) in kwargs.iteritems():
            setattr(self, _name, _value)

### attribute value types

class _Value(object):

    """Base class for element attribute values"""

    @classmethod
    def fromValue(cls, value):
        """Return new object of this class or None

        If value is an empty string or None, return None.
        Otherwise return an instance of this class
        initialized with value (may raise InvalidLiteral).

        """
        # REQUIRED must be allowed for class initialization
        if value in (None, REQUIRED):
            return value
        if isinstance(value, basestring) and (value.strip() == ""):
            return None
        return cls(value)

    def xml(self):
        """Return quoted XML representation of the attribute value"""
        return "\"%s\"" % self

class Boolean(int, _Value): # 'bool' is not an acceptable base type; use int

    """Boolean value used in element attributes"""

    def __new__(cls, value):
        """Create Boolean value

        Argument processing differs from builtin booleans:

            * if value represents an integer number,
              then zero is false and any other number is true
            * otherwise value must be one of the strings "true",
              "false", "yes" and "no" (case insensitive)
            * any other value produces an error

        """
        if isinstance(value, (float, int)):
            return int.__new__(cls, bool(value))
        # try string interpretation first because the primary use
        # is interpretation of element attribute values loaded from xml
        # unicode() is used instead of str() to avoid the need of
        # special processing of UnicodeEncodeError.  i hope it will add
        # very little overhead for ascii strings.
        _val = unicode(value).lower()
        if _val in ("true", "yes", "1"):
            _val = True
        elif _val in ("false", "no", "0"):
            _val = False
        else:
            # any non-zero integer is True
            try:
                _val = int(value)
            except ValueError:
                raise InvalidLiteral(cls, value)
            else:
                _val = bool(_val)
        return int.__new__(cls, _val)

    def __str__(self):
        """Return "true" or "false"

        This differs from builtin bool with lowercase first letter
        (because that's canonical representation for XML boolean
        data type).

        """
        return ("false", "true")[self]

    __unicode__ = __str__

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self)

class Integer(int, _Value):

    """Integer value used in element attributes"""

    def __new__(cls, value):
        try:
            return int.__new__(cls, value)
        except (TypeError, ValueError):
            raise InvalidLiteral(cls, value)

class Number(float, _Value):

    """Base class for fixed-point numeric classes, also used as integer number
    """

    # number of digits in the fractional part
    PRECISION = 0

    def __new__(cls, value):
        try:
            return float.__new__(cls, value)
        except (TypeError, ValueError):
            raise InvalidLiteral(cls, value)

    def __str__(self):
        return "%.*f" % (self.PRECISION, self)

    __repr__ = __str__

# numeric classes registry
_numeric_classes = {0: Number}

def Numeric(precision):
    """class factory: return value class for numbers with given precision

    Parameters:
        precision: number or digits in the fractional part.

    """
    # pylint: disable-msg=W0602
    # W0602: Using global for '_numeric_classes' but no assigment is done
    global _numeric_classes
    try:
        return _numeric_classes[precision]
    except KeyError:
        # pylint: disable-msg=C0111,W0104
        # W0104: Statement seems to have no effect
        # C0111: Missing docstring
        # The statement has the effect of setting the docstring.
        # and the above pylint hint doesn't help anyway.
        class _Number(Number):
            """Fixed point number with %i decimal digits""" % precision
            PRECISION = precision
        _numeric_classes[precision] = _Number
        return _Number

class Dimension(float, _Value):

    """Dimension value used for positions and sizes"""

    UNITS = {
        "mm": 25.4 / 72,
        "cm": 2.54 / 72,
        "in": 1.0 / 72,
        "pt": 1.0,
    }

    def __new__(cls, value):
        """Create Dimension value

        The initializer argument may be integer or float number of points
        (1/72 inch) or a string containing integer or float value with
        optional unit suffix:
            mm: millimeters,
            cm: centimeters,
            in: inches,
            pt: points.

        If the suffix is omitted, value is in points.

        """
        if isinstance(value, (float, int)):
            return float.__new__(cls, value)
        _val = unicode(value).strip()
        try:
            _unit = cls.UNITS[_val[-2:]]
        except KeyError:
            _unit = 1.0
        else:
            _val = _val[:-2]
        try:
            _val = float(_val)
        except ValueError:
            raise InvalidLiteral(cls, value)
        return float.__new__(cls, _val / _unit)

    def __str__(self):
        """Return dimension value in integral points"""
        return "%i" % round(self)

    __unicode__ = __str__

    def __repr__(self):
        return "<%s: %s points>" % (self.__class__.__name__, self)

class _MetaColor(type):

    """Implement access to named colors as class attributes or items"""

    def __getitem__(mcs, name):
        return mcs.names[name.upper()]

    def __getattr__(mcs, name):
        try:
            return mcs.names[name.upper()]
        except KeyError:
            raise AttributeError, name

class Color(_Value):

    """Color value"""

    __metaclass__ = _MetaColor

    names = {
        # HTML 4.01 colors
        "BLACK":   "#000000",
        "SILVER":  "#C0C0C0",
        "GRAY":    "#808080",
        "WHITE":   "#FFFFFF",
        "MAROON":  "#800000",
        "RED":     "#FF0000",
        "PURPLE":  "#800080",
        "FUCHSIA": "#FF00FF",
        "GREEN":   "#008000",
        "LIME":    "#00FF00",
        "OLIVE":   "#808000",
        "YELLOW":  "#FFFF00",
        "NAVY":    "#000080",
        "BLUE":    "#0000FF",
        "TEAL":    "#008080",
        "AQUA":    "#00FFFF",
        # awt colors
        "CYAN":      "#00FFFF",
        "DARKGRAY":  "#404040",
        "LIGHTGRAY": "#C0C0C0",
        "MAGENTA":   "#FF00FF",
        "ORANGE":    "#FFC800",
        "PINK":      "#FFAFAF",
    }

    @classmethod
    def encode(cls, color):
        """Return standard representation for any color spec

        Parameter value may be one of the following:
            * encoded string, same as output value
            * color name from the .names dictionary (case insensitive)
            * three integer values: red, green, blue (0..255)
            * three float values: red, green, blue (0..1)
            * single integer value, where
                * the red component is in bits 16-23,
                * the green component is in bits 8-15,
                * the blue component is in bits 0-7
            * string containing three comma-separated numbers
              (integer or float) or integer color number

        Return value: 6-digit hexadecimal number prefixed by a hash mark

        """
        _hexdigits = "0123456789ABCDEF"
        # if spec is a string, try to extract integer color number
        # or RGB triple
        if isinstance(color, basestring):
            if ("," in color):
                if "." in color:
                    _convert = float
                else:
                    _convert = int
                try:
                    _color = [_convert(_c) for _c in color.split(",")]
                except ValueError:
                    raise InvalidLiteral(cls, color)
            else:
                # see if it's single integer
                try:
                    _color = int(color)
                except ValueError:
                    _color = color
        elif isinstance(color, Color):
            return str(color)
        else:
            _color = color
        # check specification variants
        if isinstance(_color, basestring):
            _color = _color.upper()
            if _color in cls.names:
                return cls.names[_color]
            elif (_color[:1] == "#") and (len(_color) == 7) \
            and len([_c for _c in _color[1:] if _c in _hexdigits]) == 6:
                return _color
            else:
                raise InvalidLiteral(cls, color)
        elif isinstance(_color, (list, tuple)):
            _rgb = _color
        else:
            # _color must be integer
            try:
                _color = int(_color)
            except:
                raise InvalidLiteral(cls, color)
            if (_color < 0) or (_color >= (1 << 24)):
                raise InvalidLiteral(cls, color)
            _rgb = ((_color >> 16) & 255, (_color >> 8) & 255, _color & 255)
        # at this point, _rgb must be 3-element sequence of ints or floats
        _spec = [_c for _c in _rgb if isinstance(_c, float) and (0 <= _c <= 1)]
        if len(_spec) == 3:
            # got floats, make ints
            _rgb = [int(_c * 255) for _c in _rgb]
        _spec = [_c for _c in _rgb if isinstance(_c, int) and (0 <= _c <= 255)]
        if len(_spec) != 3:
            raise InvalidLiteral(cls, color)
        # ok, 3 integers in range
        return "#%02X%02X%02X" % tuple(_rgb)

    def __init__(self, color):
        """Set object value from color specification

        Parameter value may be any allowed color specification
        (see `encode` method for details).

        """
        super(Color, self).__init__()
        self.value = self.encode(color)

    red = property(lambda self: int(self.value[1:3], 16),
        doc="Red component")

    green = property(lambda self: int(self.value[3:5], 16),
        doc="Green component")

    blue = property(lambda self: int(self.value[5:7], 16),
        doc="Blue component")

    rgb = property(lambda self: (self.red, self.green, self.blue),
        doc="RGB triplet (integers from 0 to 255)")

    rgbf = property(lambda self: tuple(_clr / 255.0 for _clr in self.rgb),
        doc="RGB triplet (floating point values from 0.0 to 1.0)")

    def __str__(self):
        """Return standard representation of the color value"""
        return self.value

    __unicode__ = __str__

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.value)

class String(unicode, _Value):

    """String value used in element attributes"""

    # pylint: disable-msg=R0904
    # R0904: Too many public methods (39) - most come from unicode.

    def __new__(cls, value):
        try:
            return unicode.__new__(cls, value)
        except (TypeError, ValueError):
            # note: unicode errors are subclasses of ValueError
            raise InvalidLiteral(cls, value)

    def xml(self):
        """Return quoted XML representation of the attribute value"""
        return saxutils.quoteattr(self)

class Expression(String):

    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    """Python expressions used in PRT element attributes"""
    # This is same as String, put to separate class just to make things clearer

### value domains for attributes with a set of supported values

class _Codes(String):

    """String value from a domain of allowed values"""

    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    # list of allowed values for this class
    # must be overridden in subclasses
    VALUES = ()

    # TODO: ignorecase (optional, controlled by an attribute)

    def __new__(cls, value):
        if value not in cls.VALUES:
            raise InvalidLiteral(cls, value)
        return String.__new__(cls, value)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self)

class AlignHorizontal(_Codes):

    """Horizontal alignment type"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    VALUES = ("left", "center", "right")

class AlignVertical(_Codes):

    """Vertical alignment type"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    VALUES = ("top", "center", "bottom")

class BarCodeType(_Codes):

    """Bar Code type"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    VALUES = ("Code128", "Code39", "2of5i",
        "Aztec", "QR-L", "QR-M", "QR-Q", "QR-H")

class BitmapScale(_Codes):

    """Bitmap scale type"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    VALUES = ("cut", "fill", "grow")

class BitmapType(_Codes):

    """Bitmap image format"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    # TODO: list all supported image types
    VALUES = ("png", "jpeg", "gif")

class Calculation(_Codes):

    """Calculation type for report variables"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    VALUES = ("count", "list", "set", "chain", "first", "last",
        "sum", "avg", "min", "max", "std", "var")

class Compress(_Codes):

    """Compression for 'data' elements"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    VALUES = ("zlib", "bz2")

class EjectType(_Codes):

    """Type of 'eject' elements"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    VALUES = ("page", "column")

class Encoding(_Codes):

    """Binary value encoding for 'data' elements"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    VALUES = ("base64", "uu", "qp")

class PageSize(_Codes):

    """Standard paper size names, evaluating to page dimensions"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    DIMENSIONS = {
        # ISO216 paper sizes
        "A1": (Dimension("594mm"), Dimension("841mm")),
        "A2": (Dimension("420mm"), Dimension("594mm")),
        "A3": (Dimension("297mm"), Dimension("420mm")),
        "A4": (Dimension("210mm"), Dimension("297mm")),
        "A5": (Dimension("148mm"), Dimension("210mm")),
        "A6": (Dimension("105mm"), Dimension("148mm")),
        "B3": (Dimension("353mm"), Dimension("500mm")),
        "B4": (Dimension("250mm"), Dimension("353mm")),
        "B5": (Dimension("176mm"), Dimension("250mm")),
        "B6": (Dimension("125mm"), Dimension("176mm")),
        # North American paper sizes
        "BusinessCard": (Dimension("2.125in"), Dimension("3.37in")),
        "Executive": (Dimension("7.25in"), Dimension("10.5in")),
        "Ledger": (Dimension("11in"), Dimension("17in")),
        "Legal": (Dimension("8.5in"), Dimension("14in")),
        "Letter": (Dimension("8.5in"), Dimension("11in")),
        "Quatro": (Dimension("8in"), Dimension("10in")),
        "Royal": (Dimension("20in"), Dimension("25in")),
        "Statement": (Dimension("5.5in"), Dimension("8.5in")),
        # ISO269 envelope sizes (B and C series are same as page sizes)
        "EnvelopeB4": (Dimension("250mm"), Dimension("353mm")),
        "EnvelopeB5": (Dimension("176mm"), Dimension("250mm")),
        "EnvelopeC3": (Dimension("324mm"), Dimension("458mm")),
        "EnvelopeC4": (Dimension("229mm"), Dimension("324mm")),
        "EnvelopeC5": (Dimension("162mm"), Dimension("229mm")),
        "EnvelopeC6": (Dimension("114mm"), Dimension("162mm")),
        "EnvelopeDL": (Dimension("110mm"), Dimension("220mm")),
        # North American envelope sizes
        "Envelope#10": (Dimension("4.125in"), Dimension("9.5in")),
        "EnvelopeA2": (Dimension("4.375in"), Dimension("5.75in")),
        "EnvelopeA6": (Dimension("4.75in"), Dimension("6.5in")),
        "EnvelopeA7": (Dimension("5.25in"), Dimension("7.25in")),
        # More page and envelope dimensions may be added
        # See http://en.wikipedia.org/wiki/Paper_size
        # and http://en.wikipedia.org/wiki/Envelope_size
    }

    VALUES = DIMENSIONS.keys()

    dimensions = property(lambda self: self.DIMENSIONS[self],
        doc="Page dimensions (width, height)")

class PenType(_Codes):

    """Line style

    This is a surrogate class: if value may be interpreted
    as dimension, .fromValue returns Dimension instance.
    Instance of this class is returned for dashed/dotted
    hairline strokes.

    """
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    VALUES = ("dot", "dash", "dashdot")

    @classmethod
    def fromValue(cls, value):
        """Return Dimension or type code or None"""

        try:
            return Dimension.fromValue(value)
        except InvalidLiteral:
            return super(PenType, cls).fromValue(value)

class TextAlignment(_Codes):

    """Alignment type for text fields"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    VALUES = ("left", "center", "right", "justified")

class VariableIteration(_Codes):

    """Iteration/Reset type for report variables"""
    # pylint: disable-msg=R0904
    # R0904: Too many public methods - same as in the base class

    VALUES = ("report", "page", "column", "group", "detail", "item")

### XML parsing/construction

class Validator(object):

    """Base class for template/printout element validators"""

    # constants used to restrict number of occurrences for child elements
    UNRESTRICTED = 0 # don't check count, just call element validator
    ONE = 1
    ZERO_OR_ONE = 2
    ONE_OR_MORE = 3

    # common validation helpers

    class Unique(object):

        """"unique in collection" validator

        Validators of this class create collections (dictionaries) of
        named elements in the ElementTree properties.  During validation
        each object of the collection is added to collection dictionary
        raising DuplicateElement error if the name is already found.

        """

        # pylint: disable-msg=R0903
        # R0903: Too few public methods

        def __init__(self, attrname, collection_name=None):
            """Initialize uniqueness validator

            Parameters:
                attrname: name of the tree attribute for this collection
                collection_name: optional friendly name of the collection
                    used in error message.  If omitted, will be composed
                    from attrname.

            """
            self.attrname = attrname
            if collection_name is None:
                # e.g. "report groups" for attrname=="groups"
                self.collection_name = "report %s" % attrname
            else:
                self.collection_name = collection_name

        def __call__(self, tree, element, path):
            """Perform validation"""
            try:
                _collection = getattr(tree, self.attrname)
            except AttributeError:
                _collection = {}
                setattr(tree, self.attrname, _collection)
            _name = element.get("name", "")
            if not _name:
                raise MissingRequiredAttribute("name", element, path)
            elif _name in _collection:
                raise DuplicateElement(_name, self.collection_name,
                    element, path)
            _collection[_name] = element

    # custom validation functions
    prevalidate = ()
    validate = ()

    def __init__(self, tag, attributes=None, children=(),
        prevalidate=None, validate=None, doc=None
    ):
        """Create an element validator object

        Parameters:
            tag: element tag name.
            attributes: element attribute definitions.
                If passed, must be a dictionary where
                keys are attribute names, values are
                (class, default) pairs.
            children: child element restrictions.
                A sequence of (validator, restriction) pairs
                where validator is object of this class
                and restriction is one of the occurrence
                restriction constants defined in this class.
            prevalidate: optional validation function or list
                of functions to call before standard validation.
            validate: optional validation function or list
                of functions to call after standard validation.
            doc: optional docstring for the validator object.

        Validation functions (prevalidate and validate) receive
        same arguments as the validation method of this class.

        """
        self.tag = tag
        if attributes:
            self.attributes = dict([(_name, (_cls, _cls.fromValue(_default)))
                for (_name, (_cls, _default)) in attributes.iteritems()])
        else:
            self.attributes = {}
        self.children = children
        # W0612: Unused variable '_restrict'
        self.child_validators = dict([(_validator.tag, _validator)
            for (_validator, _restrict) in children])
        if prevalidate is not None:
            if isinstance(prevalidate, (list, tuple)):
                self.prevalidate = prevalidate
            else:
                self.prevalidate = (prevalidate,)
        if validate is not None:
            if isinstance(validate, (list, tuple)):
                self.validate = validate
            else:
                self.validate = (validate,)
        if doc:
            self.__doc__ = doc

    def __call__(self, tree, element, path):
        """Validate an XML element

        Parameters:
            tree: ElementTree object.  Since we cannot attach properties
                to element nodes, this is the only object that can hold
                validation state.  Validators will add attributes to the
                tree.  It may also be useful to find parent nodes.
            element: an element of the tree
            path: element path in the tree (abbreviated XPath syntax)

        """
        # call initial validation, if any
        for _validate in self.prevalidate:
            _validate(tree, element, path)
        # verify attributes: convert XML values, apply defaults
        _attrib = element.attrib
        for (_name, (_cls, _default)) in self.attributes.iteritems():
            _value = _attrib.get(_name, "")
            if _value != "":
                try:
                    _value = _cls.fromValue(_attrib[_name])
                except:
                    (_err, _tb) = sys.exc_info()[1:]
                    raise AttributeConversionError(_name, _value, _err,
                        element, path), None, _tb
            elif _default is REQUIRED:
                raise MissingRequiredAttribute(_name, element, path)
            else:
                _value = _default
            element.set(_name, _value)
        # verify child elements: check the number of occurrences,
        # call child validators.
        for (_validator, _restrict) in self.children:
            _tag = _validator.tag
            _children = element.findall(_tag)
            # check restrictions
            _is_collection = _restrict not in (self.ONE, self.ZERO_OR_ONE)
            if (not _is_collection) and (len(_children) > 1):
                raise ChildMustBeOne(_tag, element, path)
            if (_restrict in (self.ONE, self.ONE_OR_MORE)) \
            and (len(_children) < 1):
                raise MissingRequiredChild(_tag, element, path)
            # validate each child
            _path = _collection_path = "/".join((path, _tag))
            _idx = 0
            for _child in _children:
                if _is_collection:
                    _idx += 1
                    _path = "%s[%i]" % (_collection_path, _idx)
                _validator(tree, _child, _path)
        # apply custom validation, if any
        for _validate in self.validate:
            _validate(tree, element, path)

    def starttag(self, element):
        """Return XML start tag with filled attributes

        Parameters:
            element: tree element of type handled by this validator

        """
        _items = [element.tag]
        for (_name, _val) in sorted(element.items()):
            try:
                _default = self.attributes[_name][1]
            except KeyError:
                # ignore undeclared attributes
                continue
            # don't output default values
            if _val == _default:
                continue
            try:
                _val = _val.xml()
            except AttributeError:
                # _val is not instance of attribute value classes
                # try simple conversion
                _val = saxutils.quoteattr(unicode(_val))
            _items.append("=".join((_name, _val)))
        return " ".join(_items)

    def writexml(self, writer, element, encoding="utf-8",
        indent="", addindent=" ", newl="\n"
    ):
        """Write XML to the writer object

        Parameters:
            writer: file-like output object
            element: tree element of type handled by this validator
            encoding: character set name
            indent: indentation of the current element
            addindent: incremental indentation to use for child elements
            newl: string used to put each element on different line

        """
        _starttag = self.starttag(element).encode(encoding,
            "xmlcharrefreplace")
        # collect known children
        _child_elements = []
        for _child in getchildren(element):
            try:
                _validator = self.child_validators[_child.tag]
            except KeyError:
                pass
            else:
                _child_elements.append((_child, _validator))
        if _child_elements:
            writer.write("%s<%s>%s" % (indent, _starttag, newl))
            for (_child, _validator) in _child_elements:
                _validator.writexml(writer, _child, encoding,
                    indent + addindent, addindent, newl)
            writer.write("%s</%s>%s" % (indent, self.tag, newl))
        else:
            writer.write("%s<%s />%s" % (indent, _starttag, newl))

class DataBlock(Validator):

    """A block of data in report templates and printouts

    Raw data may be any object that can be pickled
    if "pickle" is set to True.  If "pickle" is False
    (default), raw data must be encoded (8-bit) string
    if "encoding" is set, or unicode string if "encoding"
    is unset, or None.

    For binary or compressed or pickled data "encoding"
    must be set to "base64" or "uu".

    """

    @staticmethod
    def collect(tree, *args, **kwargs):
        """Build collection of toplevel data blocks

        Collect all "data" children of the root element of the tree.
        Check that each data element has a name and that all names
        are unique.  Put the collection in "datablocks" property of
        the tree.

        Note: for other collections (fonts, variables etc.) this
        is done by Unique() validator.  Data blocks cannot use it
        because the collection must contain only blocks defined
        as children of the root element.  Data blocks put in report
        elements (images, bar codes, text fields) do not participate
        in this collection; they are not required to have a name and
        cannot be referred.

        Additional arguments are ignored; they are defined to allow
        this function to be used in common validation sequences.

        """
        _collection = {}
        _root = tree.getroot()
        _idx = 0
        for _child in _root.findall("data"):
            _idx += 1
            _name = _child.get("name")
            if not _name:
                raise MissingRequiredAttribute("name",
                    _child, "/%s/data[%i]" % (_root.tag, _idx))
            if _name in _collection:
                raise DuplicateElement(_name, "report-level data elements",
                    _child, "/%s/data[%i]" % (_root.tag, _idx))
            _collection[_name] = _child
        tree.datablocks = _collection

    @staticmethod
    def make_element(parent, attrib, data):
        """Create an XML element from attributes and data

        Parameters:
            parent: parent element in the tree
            attrib: attribute dictionary
            data: raw output data

        The data will be compressed and encoded as specified
        in the attributes and put to the element text.

        Return value: ElementTree element.

        """
        _elem = ET.SubElement(parent, "data", attrib)
        if not data:
            return _elem
        if attrib.get("pickle"):
            _data = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
        elif data is None:
            # don't encode data
            return _elem
        else:
            # start with plaintext contents
            _data = data
        _compress = attrib.get("compress")
        if _compress == "zlib":
            _data = zlib.compress(_data)
        elif _compress == "bz2":
            _data = bz2.compress(_data)
        _encoding = attrib.get("encoding")
        if _encoding == "base64":
            _data = binascii.b2a_base64(_data)
            _data = "\n".join([""] + [_data[_ii:_ii + 76]
                for _ii in xrange(0, len(_data), 76)])
        elif _encoding == "uu":
            _data = "".join(["\n"] + [binascii.b2a_uu(_data[_ii:_ii + 45])
                for _ii in xrange(0, len(_data), 45)])
        elif _encoding == "qp":
            _data = "\n" + binascii.b2a_qp(_data, True, False) + "\n"
        else:
            # encoded data is ASCII.  non-encoded must be unicode.
            _data = unicode(_data)
        _elem.text = _data
        return _elem

    @staticmethod
    def get_data(element, context=None):
        """Return raw data from a DataBlock element

        Parameters:
            element: XML element of type "data"
            context: expression evaluation context
                for data blocks that have an "expr" attribute.
                If "expr" attribute is set and context is None,
                raise MissingContextError.

        """
        _expr = element.get("expr")
        if _expr:
            if context is None:
                raise MissingContextError(_expr, element)
            return context.eval(_expr, element)
        _data = element.text
        # empty xml string is None dependless of encoding/compression/pickling
        if not _data:
            return None
        _encoding = element.get("encoding")
        if _encoding == "base64":
            _data = binascii.a2b_base64(_data)
        elif _encoding == "uu":
            _data = binascii.a2b_uu(_data)
        elif _encoding == "qp":
            # .write() adds blank space to encoded data.
            # it must be stripped here or it will be
            # escaped on repeated write
            _data = binascii.a2b_qp(_data.strip())
        _compress = element.get("compress")
        if _compress == "zlib":
            _data = zlib.decompress(_data)
        elif _compress == "bz2":
            _data = bz2.decompress(_data)
        if element.get("pickle"):
            _data = pickle.loads(_data)
        return _data

    def writexml(self, writer, element, encoding="utf-8",
        indent="", addindent=" ", newl="\n"
    ):
        """Write XML to the writer object

        Parameters:
            writer: file-like object with "write" method
                able to accept unicode strings
            element: tree element of type handled by this validator
            encoding: character set name
            indent: indentation of the current element
            addindent: incremental indentation to use for child elements
            newl: string used to put each element on different line

        """
        # pylint: disable-msg=W0613
        # W0613: Unused argument 'addindent' - API comes from Validator,
        #   but there are no child elements in the data element
        _text = element.text or ""
        if element.get("encoding"):
            _indent2 = indent
            # we will be adding certain amount of space before the closing tag
            # to make it certain amount indeed, make sure there aren't any
            # spaces yet.
            _text = _text.rstrip(" ")
        else:
            # must not add blank spaces to non-encoded values
            _indent2 = ""
        # there are no children for this element, just text
        _text = u"%s<%s>%s%s</%s>%s" % (indent, self.starttag(element),
            saxutils.escape(_text), _indent2, self.tag, newl)
        writer.write(_text.encode(encoding, "xmlcharrefreplace"))

class ElementTree(ET.ElementTree):

    """XML reader/writer for template/printout trees"""

    filename = None # set by .parse()

    def __init__(self, validator, element=None, file=None):
        """Initialize the tree

        Parameters:
            validator: Validator object for the root node
            element: optional root element
            file: optional file handle or name
                if passed, the tree is loaded from this file

        """
        # pylint: disable-msg=W0231,W0622
        # W0231: __init__ method from base class 'ElementTree' is not called
        #   - ain't it?
        # W0622: Redefining built-in 'file' - the name comes from base class

        # FIXME: this instantiation seems to be obsolete
        if isinstance(validator, type):
            self.root_validator = validator()
        else:
            self.root_validator = validator
        ET.ElementTree.__init__(self, element=element, file=file)

    def validate(self):
        """Prepare the tree for use in processing programs"""
        _root = self.getroot()
        self.root_validator(self, _root, "/" + _root.tag)

    def parse(self, source, parser=None):
        """Parse source file and validate loaded tree"""
        _root = ET.ElementTree.parse(self, source, parser)
        if isinstance(source, basestring):
            self.filename = source
        else:
            self.filename = None
        # Guess the reason for loading a tree is to use it.
        # Make sure the tree is usable.
        self.validate()
        return _root

    def write(self, file, encoding="utf-8"):
        """Write the tree to an XML file

        Parameters:
            file: file name or file object opened for writing
            encoding: optional output encoding (default is "utf-8")

        Differences from elementtree:
            - encoding defaults to "utf-8"
            - output is indented

        """
        # pylint: disable-msg=C0103,W0622
        # C0103: Invalid names "file", "encoding" - fancy defaults
        # W0622: Redefining built-in 'file' - the name comes from base class
        assert self._root is not None
        if not hasattr(file, "write"):
            file = open(file, "wb")
        if not encoding:
            encoding = "utf-8"
        elif encoding not in ("utf-8", "us-ascii"):
            file.write("<?xml version='1.0' encoding='%s'?>\n" % encoding)
        self.root_validator.writexml(file, self._root, encoding)

    def __str__(self):
        """Return string representation of the tree"""
        _stream = StringIO()
        self.write(_stream)
        return _stream.getvalue()

    def getchildren(self, element=None):
        """Return a list of child elements

        Pararmeters:
            element: Optional parent element to iterate over.

                If omitted, use the root element of the tree.

        Return: a list of Element objects.

        """
        if element is None:
            element = self.getroot()
        return getchildren(element)

    def copy(self, element):
        """Return a shallow copy of the element

        Create a new Element with the same tag, attributes and text
        and return it.

        """
        _rv = Element(element.tag, element.attrib)
        _rv.text = element.text
        return _rv

### elements common for templates and printouts

Font = Validator(tag="font",
    validate=Validator.Unique("fonts"),
    attributes={
        "name": (String, REQUIRED),
        "typeface": (String, REQUIRED),
        "size": (Integer, REQUIRED),
        "bold": (Boolean, False),
        "italic": (Boolean, False),
        "underline": (Boolean, False),
    }, doc="Font definition for use in text fields")

### structures used in processing

class Box(object):

    """Rectangular space occupied by report elements and sections"""

    DEFAULTS = (
        ("x", 0),
        ("y", 0),
        ("width", -1),
        ("height", -1),
        ("halign", AlignHorizontal("left")),
        ("valign", AlignVertical("bottom")),
        ("float", False),
    )

    __slots__ = map(lambda x: x[0], DEFAULTS)

    # dimensions must be rounded after each calculation.
    # (got height=-5.6843418860808015e-014 which raised
    # error in assert self.height >= 0).
    # this is number of decimal digits to keep after round()
    PRECISION = 3

    left = property(lambda self: self.x, doc="Position of the left margin")
    right = property(lambda self: self.x + self.width,
        doc="Position of the right margin")
    top = property(lambda self: self.y, doc="Position of the top margin")
    bottom = property(lambda self: self.y + self.height,
        doc="Position of the bottom margin")

    def __init__(self, *args, **kwargs):
        _attrs = dict(self.DEFAULTS)
        _attrs.update(dict(zip(self.__slots__, args)))
        _attrs.update(kwargs)
        for (_name, _value) in _attrs.iteritems():
            setattr(self, _name, _value)

    def copy(self, dimensions_only=False):
        """Return a copy of this Box

        Parameters:
            dimensions_only: if True, only dimension attributes
                (position and size) are copied to new Box.
                Otherwise copy all attribute slots (default).

        """
        if dimensions_only:
            _attrs = ("x", "y", "width", "height")
        else:
            _attrs = self.__slots__
        return self.__class__(**dict([(_name, getattr(self, _name))
            for _name in _attrs]))

    @classmethod
    def from_element(cls, element):
        """Create new Box object from XML element

        Parameters:
            element: "box" element from template tree or None.
                Must be already validated by the Box validator.

        """
        if element is None:
            _args = {}
        else:
            _args = dict([(_name, element.get(_name, _default))
                for (_name, _default) in cls.DEFAULTS])
        return cls(**_args)

    def make_element(self, parent):
        """Append box subelement to an element of printout tree"""
        # Note: cannot use self.__slots__ here
        # because printout boxes don't have alignment attributes
        _attrs = dict([(_name, Dimension(getattr(self, _name)))
            for _name in ("x", "y", "width", "height")])
        return SubElement(parent, "box", _attrs)

    def place_x(self, box):
        """Perform horizontal placement of this box

        Parameters:
            box: bounding box

        Assume that current horizontal position and size are
        relative to given area dimensions (negative values are
        offset from right margin) and make them absolute.

        """
        if self.x < 0:
            self.x += box.width + 1
        self.x = round(self.x + box.x, self.PRECISION)
        if self.width < 0:
            self.width = round(
                (self.width + box.width + 1 + box.x - self.x), self.PRECISION)

    def place_y(self, box):
        """Perform vertical placement of this box

        Parameters:
            box: bounding box

        Assume that current vertical position and size are
        relative to given area dimensions (negative values
        are offset from bottom margin) and make them absolute.

        """
        if self.y < 0:
            self.y += box.height + 1
        self.y = round(self.y + box.y, self.PRECISION)
        if self.height < 0:
            self.height = round(
                (self.height + box.height + 1 + box.y - self.y),
                self.PRECISION)

    def align_x(self, box):
        """Perform horizontal alignment within bounding box

        Parameters:
            box: bounding box

        Set x position according to halign attribute.
        Current x position is discarded.

        """
        assert self.width >= 0
        assert box.width >= 0
        if self.halign == "center":
            self.x = box.x + int((box.width - self.width) / 2)
        elif self.halign == "right":
            self.x = box.x + box.width - self.width
        else:
            self.x = box.x

    def align_y(self, box):
        """Perform vertical alignment within bounding box

        Parameters:
            box: bounding box

        Set y position according to valign attribute.
        Current y position is discarded.

        """
        assert self.height >= 0
        assert box.height >= 0
        if self.valign == "center":
            self.y = box.y + int((box.height - self.height) / 2)
        elif self.valign == "bottom":
            self.y = box.y + box.height - self.height
        else:
            self.y = box.y

    def place(self, box):
        """Place the box in given area

        Parameters:
            box: bounding box

        Assume that current position and size are relative
        to given area dimensions (negative values are offset
        from right/bottom margins) and make them absolute.
        Adjust position for horizontal and vertical alignments.

        """
        self.place_x(box)
        self.align_x(box)
        self.place_y(box)
        self.align_y(box)

    def rescale(self, scale_x, scale_y=None):
        """Change the box dimensions in-place by scaling them

        Parameters:
            scale_x: horizontal scaling factor
            scale_y: optional vertical scaling factor.
                if omitted or None, use scale_x.

        """
        # pylint: disable-msg=C0103
        # C0103: Invalid name "scale_y" - fancy default
        if scale_y == None:
            scale_y = scale_x
        self.x = round(self.x * scale_x, self.PRECISION)
        self.y = round(self.y * scale_y, self.PRECISION)
        self.width = round(self.width * scale_x, self.PRECISION)
        self.height = round(self.height * scale_y, self.PRECISION)

    def __repr__(self):
        return "<%s@%X: %.1f, %.1f, %.1f, %.1f>" % (self.__class__.__name__,
            id(self), self.x, self.y, self.width, self.height)

# export constants and all non-private callables and constants
__all__ = ["REQUIRED", "NOTHING", "Font"] + [
    _global_name for (_global_name, _global_item) in globals().items()
    if callable(_global_item) and not _global_name.startswith("_")
]
del _global_name, _global_item

# vim: set et sts=4 sw=4 :
