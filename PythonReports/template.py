"""PythonReports Template (PRT) structures"""
"""History (most recent first):
15-dec-2006 [als]   Eject type defaults to "page"
15-dec-2006 [als]   allow empty detail section;
                    fix Layout: require either pagesize or width and height
15-dec-2006 [als]   group header an footer renamed to title and summary
07-dec-2006 [als]   added Rectangle.opaque
07-dec-2006 [als]   removed "transparent" attribute of the "box" element
05-dec-2006 [als]   style: imports come after version, date and exports;
                    sweep pylint warnings
20-oct-2006 [als]   Barcode X dimension attr renamed to "module"
22-sep-2006 [als]   BarCode: X dimension is a number of mills
06-sep-2006 [als]   Box sizes default to -1
29-aug-2006 [als]   fix Variable: default value for "reset" is "report"
26-jul-2006 [als]   Group: add self reference to .child_validators
25-jul-2006 [als]   Report: create report-level collections in prevalidator
21-jul-2006 [als]   Element classes changed to element validators;
                    export "Data" and "Font" definitions (from datatypes)
17-jul-2006 [als]   add missing "eject" child to section elements
14-jul-2006 [als]   fix Eject.when: default was False (contrary to docs),
                    use None to skip unneded evaluations
12-jul-2006 [als]   Style: "printwhen" defaults to unset value
10-jul-2006 [als]   BarCode: added "vertical" attribute
06-jul-2006 [als]   added export declaration
04-jul-2006 [als]   created
"""
__version__ = "$Revision: 1.7 $"[11:-2]
__date__ = "$Date: 2006/12/15 13:24:48 $"[7:-2]

__all__ = [
    "Parameter", "Variable", "Import", "Data", "Font",
    "Style", "Box", "Eject",
    "Field", "Line", "Rectangle", "Image", "BarCode",
    "Detail", "Header", "Footer", "Title", "Summary",
    "Columns", "Group", "Layout", "Report", "load",
]

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

Field = Validator(tag="field",
    attributes={
        "expr": (Expression, None),
        "evaltime": (String, None), # may be "report", "page", "column"
                                    # or group name
        "data": (String, None),     # name of external 'data' element
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
    of with a pair of "width" and "height".  If neither is set, it's an error.

    """
    # pylint: disable-msg=W0613
    # W0613: Unused argument 'tree'
    if element.get("pagesize"):
        return
    if element.get("width") and element.get("height"):
        return
    raise XmlValidationError(
        "Must have either 'pagesize' or 'width' and 'height'", element, path)

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
    """Load printout file, return ElementTree"""
    _et = ElementTree(Report)
    _et.parse(source)
    return _et

# vim: set et sts=4 sw=4 :
