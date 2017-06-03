"""PythonReports Template (PRT) structures"""

__all__ = [
    "Parameter", "Variable", "Import", "Data", "Font",
    "Style", "Box", "Eject", "Embedded", "Outline",
    "Field", "Line", "Rectangle", "Image", "BarCode",
    "Detail", "Header", "Footer", "Title", "Summary",
    "Columns", "Group", "Layout", "Report", "load",
]

import os

from PythonReports.datatypes import *

Parameter = Validator(tag="parameter",
    validate=Validator.Unique("parameters"),
    attributes={
        "name": (String, REQUIRED),
        "default": (Expression, REQUIRED),
        "prompt": (Boolean, False),
    }, doc="Report generation parameters"
)

Variable = Validator(tag="variable",
    validate=Validator.Unique("variables"),
    attributes={
        "name": (String, REQUIRED),
        "expr": (Expression, REQUIRED),
        "init": (Expression, None),
        "calc": (Calculation, "first"),
        "iter": (VariableIteration, "detail"),
        "itergrp": (String, None),
        "reset": (VariableIteration, "report"),
        "resetgrp": (String, None),
    }, doc="""Report variable

    Used to run counters, sums and such.

    """
)

Import = Validator(tag="import",
    attributes={
        "path": (String, REQUIRED),
        "alias": (String, None),
    },
    doc="Import a symbol from Python module into expression evaluation context"
)

Data = DataBlock(tag="data",
    attributes={
        "name": (String, None),
        "pickle": (Boolean, False),
        "compress": (Compress, None),
        "encoding": (Encoding, None),
        "expr": (Expression, None),
    })

def Style(tree, element, path):
    """Additional validator for "style" elements

    If "font" attribute is set, check that its' value is known
    font definition name.

    """
    _font = element.get("font")
    if _font and (_font not in tree.fonts):
        raise XmlValidationError(
            "No font definition found for name '%s'" % _font,
            element, path)

Style = Validator(tag="style", validate=Style,
    attributes={
        "when": (Expression, "True"),
        "printwhen": (Expression, None),
        "font": (String, None),
        "color": (Color, None),
        "bgcolor": (Color, None),
    }, doc="A set of formatting characteristics for report elements"
)

Box = Validator(tag="box",
    attributes={
        "x": (Dimension, 0),
        "y": (Dimension, 0),
        "float": (Boolean, False),
        "width": (Dimension, -1),
        "height": (Dimension, -1),
        "halign": (AlignHorizontal, "left"),
        "valign": (AlignVertical, "bottom"),
    }, doc="Defines rectangular space occupied by report elements"
)

Eject = Validator(tag="eject",
    attributes={
        "type": (EjectType, "page"),
        "require": (Dimension, None),
        "when": (Expression, None),
    },
    doc="""Tells when section elements must be started on a new page or column

    For the title section, eject is evaluated at the end of the section,
    for all other sections - at the beginning of the section.

    """
)

Outline = Validator(tag="outline",
    attributes={
        "title": (Expression, REQUIRED),
        "level": (Integer, 1),
        "closed": (Boolean, False),
    },
    doc="A bookmark for document outline navigation"
)

Arg = Validator(tag="arg",
    attributes={
        "name": (String, REQUIRED),
        "value": (Expression, REQUIRED),
    },
    doc="Actual argument value passed to subreport to fill a parameter slot"
)

def _need_template_or_embedded(tree, element, path):
    """Additional validation for "subreport" elements

    The element must have either "template" or "embedded" attribute,
    but not both of them.

    """
    # pylint: disable-msg=W0613
    # W0613: Unused argument 'tree'
    _template = element.get("template")
    _embedded = element.get("embedded")
    if _template and _embedded:
        raise XmlValidationError("Found both 'template' and 'embedded'",
            element, path)
    elif not (_template or _embedded):
        raise XmlValidationError(
            "Either 'template' or 'embedded' attribute is required",
            element, path)

# TODO subreport validation:
#   - cannot be placed in a column
#   - if inline is True, ownpageno must be False.
Subreport = Validator(tag="subreport",
    validate=(
        _need_template_or_embedded,
    ), attributes={
        "template": (String, None),
        "embedded": (String, None),
        "seq": (Integer, REQUIRED),
        "data": (Expression, REQUIRED),
        "when": (Expression, None),
        "inline": (Boolean, False),
        "ownpageno": (Boolean, False),
    }, children=(
        (Arg, Validator.UNRESTRICTED),
    ), doc="Sets an embedded report to run on an inner data sequence"
)

Field = Validator(tag="field",
    attributes={
        "expr": (Expression, None),
        "evaltime": (String, None), # may be "report", "page", "column"
                                    # or group name
        "data": (String, None), # name of external 'data' element
        "align": (TextAlignment, "left"),
        "format": (String, "%s"),
        "stretch": (Boolean, False),
    }, children=(
        (Box, Validator.ZERO_OR_ONE),
        (Style, Validator.UNRESTRICTED),
        (Data, Validator.ZERO_OR_ONE),
    ), doc="""A text field

    Contents of the field may be set by 'expr' or 'data' attributes
    or by child data element.  Data may be set (either by attribute
    or by child element) along with 'expr' to estimate field size
    when 'expr' evaluation is delayed by non-empty 'evaltime'.
    When evaluation time arrives, the field is filled with 'expr' result.

    """
)

Line = Validator(tag="line",
    attributes={
        "pen": (PenType, REQUIRED),
        "backslant": (Boolean, False),
    }, children=(
        (Box, Validator.ZERO_OR_ONE),
        (Style, Validator.UNRESTRICTED),
    ), doc="A (straight) line"
)

Rectangle = Validator(tag="rectangle",
    attributes={
        "pen": (PenType, REQUIRED),
        "radius": (Dimension, 0),
        "opaque": (Boolean, True),
    }, children=(
        (Box, Validator.ZERO_OR_ONE),
        (Style, Validator.UNRESTRICTED),
    ), doc="A rectangle"
)

Image = Validator(tag="image",
    attributes={
        "type": (BitmapType, REQUIRED),
        "file": (String, None),
        "data": (String, None),
        "scale": (BitmapScale, "cut"),
        "proportional": (Boolean, True),
        "embed": (Boolean, True),
    }, children=(
        (Box, Validator.ZERO_OR_ONE),
        (Style, Validator.UNRESTRICTED),
        (Data, Validator.ZERO_OR_ONE),
    ), doc="""A bitmap image

    The bitmap may be loaded from a file or from a 'data' element
    (either put in the image element or referred by the 'data' attribute.)

    """
)

BarCode = Validator(tag="barcode",
    attributes={
        "type": (BarCodeType, REQUIRED),
        "module": (Numeric(1), 10),
        "vertical": (Boolean, False),
        "grow": (Boolean, False),
        "expr": (Expression, None),
        "data": (String, None),
    }, children=(
        (Box, Validator.ZERO_OR_ONE),
        (Style, Validator.UNRESTRICTED),
        (Data, Validator.ZERO_OR_ONE),
    ), doc="""A bar code image

    The box of this element always grows in the direction of coding
    (vertically if vertical="yes", horizontally otherwise).
    Bar code images are always embedded in the PRP file.

    Code contents may be set by 'expr' or 'data' attributes or by child
    'data' element.  Data may be set (either by attribute or by child
    element) along with 'expr' to estimate image size when 'expr'
    evaluation is delayed by non-empty 'evaltime'.  When evaluation time
    arrives, 'expr' result produces the bar code image.

    Characters that cannot be encoded with selected code type are ignored.

    """
)

# common set of child validators for all section elements
_section_children = (
    (Subreport, Validator.UNRESTRICTED),
    (Box, Validator.ZERO_OR_ONE),
    (Style, Validator.UNRESTRICTED),
    (Eject, Validator.UNRESTRICTED),
    (Field, Validator.UNRESTRICTED),
    (Line, Validator.UNRESTRICTED),
    (Rectangle, Validator.UNRESTRICTED),
    (Image, Validator.UNRESTRICTED),
    (BarCode, Validator.UNRESTRICTED),
)

Detail = Validator(tag="detail", children=_section_children,
    doc="The detail section, built once for each item in the report data set"
)

Header = Validator(tag="header", children=_section_children,
    doc="Page or column header section"
)

Footer = Validator(tag="footer", children=_section_children,
    doc="Page or column footer section"
)

Title = Validator(tag="title", children=_section_children,
    attributes={
        "swapheader": (Boolean, False),
    }, doc="A summary section printed before data"
)

Summary = Validator(tag="summary", children=_section_children,
    attributes={
        "swapfooter": (Boolean, False),
    }, doc="A summary section printed after data"
)

Columns = Validator(tag="columns",
    attributes={
        "count": (Integer, REQUIRED),
        "gap": (Dimension, 0),
    }, children=(
        (Style, Validator.UNRESTRICTED),
        (Header, Validator.ZERO_OR_ONE),
        (Footer, Validator.ZERO_OR_ONE),
    ), doc="Arranges the report or data group for multi-column output"
)

def _need_subgroup_or_detail(tree, element, path):
    """Additional validation for "group" and "layout" elements

    The element must have either Group or Detail child.

    """
    # pylint: disable-msg=W0613
    # W0613: Unused argument 'tree'
    _have_group = element.find("group") is not None
    _have_detail = element.find("detail") is not None
    if _have_group and _have_detail:
        raise XmlValidationError("Found both 'group' and 'detail'",
            element, path)
    elif not (_have_group or _have_detail):
        raise XmlValidationError(
            "Either 'group' or 'detail' child is required", element, path)

Group = Validator(tag="group",
    validate=(
        _need_subgroup_or_detail,
        Validator.Unique("groups"),
    ), attributes={
        "name": (String, REQUIRED),
        "expr": (Expression, REQUIRED),
    }, children=[
        (Style, Validator.UNRESTRICTED),
        (Title, Validator.ZERO_OR_ONE),
        (Summary, Validator.ZERO_OR_ONE),
        (Columns, Validator.ZERO_OR_ONE),
        (Detail, Validator.ZERO_OR_ONE),
    ], doc="Defines a data-based group of report records"
)

# patch CHILDREN to include the Group class itself
# XXX it is possible to do this in less hackerish way:
#   define special validator placeholder (e.g. None)
#   in the child sequence to be replaced by self
#   in the validator constructor.  do we need this?
Group.children.append((Group, Validator.ZERO_OR_ONE))
Group.child_validators["group"] = Group

def _need_pagesize(tree, element, path):
    """Additional validator for "layout" element: check for page dimensions

    Page size may be specified either with the "pagesize" attribute
    or with a pair of "width" and "height".  If neither is set, it's an error.

    """
    # pylint: disable-msg=W0613
    # W0613: Unused argument 'tree'
    if element.get("pagesize"):
        return
    if element.get("width") and element.get("height"):
        return
    raise XmlValidationError(
        "Must have either 'pagesize' or 'width' and 'height'", element, path)

class EmbeddedValidator(Validator):

    """A validator for embedded reports

    The "embedded" element is an isolated sub-tree, it
    must have own namespaces for Unique property checking.

    We achieve that by creating a temporary ElementTree object
    to validate the sub-tree separately from the parent tree.

    """


    def __init__(self, tag, attributes=None, children=(),
        prevalidate=None, validate=None, doc=None,
    ):
        super(EmbeddedValidator, self).__init__(tag,
            attributes=attributes, children=children,
            prevalidate=prevalidate, validate=validate, doc=doc)
        # The Unique validator must run in the context of parent tree
        self.validate_unique = Validator.Unique("embedded")

    def __call__(self, tree, element, path):
        self.validate_unique(tree, element, path)
        _subtree = ElementTree(element)
        _subtree.filename = tree.filename
        # Embedded reports use fonts and named data blocks from main
        _subtree.fonts = dict(tree.fonts)
        _subtree.datablocks = dict(tree.datablocks)
        super(EmbeddedValidator, self).__call__(_subtree, element, path)

Embedded = EmbeddedValidator(tag="embedded",
    validate=(
        _need_subgroup_or_detail,
    ), attributes={
        "name": (String, REQUIRED),
    }, children=[
        (Parameter, Validator.UNRESTRICTED),
        (Variable, Validator.UNRESTRICTED),
        (Style, Validator.UNRESTRICTED),
        (Title, Validator.ZERO_OR_ONE),
        (Summary, Validator.ZERO_OR_ONE),
        (Header, Validator.ZERO_OR_ONE),
        (Footer, Validator.ZERO_OR_ONE),
        (Columns, Validator.ZERO_OR_ONE),
        (Detail, Validator.ZERO_OR_ONE),
        (Group, Validator.ZERO_OR_ONE),
    ], doc="An embedded subreport layout definition"
)

# patch CHILDREN to include the Embedded class itself
Embedded.children.append((Embedded, Validator.UNRESTRICTED))
Embedded.child_validators["embedded"] = Embedded

Layout = Validator(tag="layout",
    prevalidate=Data.collect,
    validate=(
        _need_pagesize,
        _need_subgroup_or_detail,
    ), attributes={
        "pagesize": (PageSize, None),
        "width": (Dimension, None),
        "height": (Dimension, None),
        "landscape": (Boolean, False),
        "leftmargin": (Dimension, 0),
        "rightmargin": (Dimension, 0),
        "topmargin": (Dimension, 0),
        "bottommargin": (Dimension, 0),
    }, children=(
        (Style, Validator.UNRESTRICTED),
        (Embedded, Validator.UNRESTRICTED),
        (Title, Validator.ZERO_OR_ONE),
        (Summary, Validator.ZERO_OR_ONE),
        (Header, Validator.ZERO_OR_ONE),
        (Footer, Validator.ZERO_OR_ONE),
        (Columns, Validator.ZERO_OR_ONE),
        (Detail, Validator.ZERO_OR_ONE),
        (Group, Validator.ZERO_OR_ONE),
    ), doc="Topmost element of report layout definition"
)

def Report(tree, element, path):
    """Prevalidator for "report" element: initialize template structures"""
    # pylint: disable-msg=W0613
    # W0613: Unused arguments 'element', 'path'

    # these collections may also be initialized by Unique constraints,
    # but we want them to be present always, even if there are no
    # elements in some collection (makes processing easier)
    tree.parameters = {}
    tree.variables = {}
    tree.groups = {}
    tree.fonts = {}
    tree.embedded = {}
    # Keep the filename if present
    # (repeated validation after the template is loaded)
    if not hasattr(tree, "filename"):
        tree.filename = None
    # don't create datablocks here - will be done in Layout prevalidator

Report = Validator(tag="report", prevalidate=Report,
    attributes={
        "name": (String, None),
        "description": (String, None),
        "version": (String, None),
        "author": (String, None),
        "basedir": (String, None),
    }, children=(
        (Parameter, Validator.UNRESTRICTED),
        (Import, Validator.UNRESTRICTED),
        (Variable, Validator.UNRESTRICTED),
        (Font, Validator.UNRESTRICTED),
        (Data, Validator.UNRESTRICTED),
        (Layout, Validator.ONE),
    ), doc="The root element of template tree"
)

def load(source):
    """Load template file, return ElementTree"""
    _et = ElementTree(Report)
    _et.parse(source)
    if isinstance(source, basestring) and os.path.exists(source):
        # XXX bad heuristics
        _et.filename = source
    return _et

# vim: set et sts=4 sw=4 :
