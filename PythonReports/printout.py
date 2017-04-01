"""PythonReports Printout (PRP) structures"""

__all__ = [
    "Text", "Line", "Rectangle", "Image", "BarCode", "Outline",
    "Box", "Page", "Data", "Font", "Printout", "load",
]

from PythonReports.datatypes import *

Box = Validator(tag="box",
    attributes={
        "x": (Dimension, REQUIRED),
        "y": (Dimension, REQUIRED),
        "width": (Dimension, REQUIRED),
        "height": (Dimension, REQUIRED),
    }, doc="""Defines rectangular space occupied by report elements

    Required child for all elements placed in pages,
    i.e. text, line, rectangle and image.

    """)

Data = DataBlock(tag="data",
    attributes={
        "name": (String, None),
        "pickle": (Boolean, False),
        "compress": (Compress, None),
        "encoding": (Encoding, None),
    })

Text = Validator(tag="text",
    attributes={
        "font": (String, REQUIRED),
        "align": (TextAlignment, "left"),
        "color": (Color, REQUIRED),
    }, children=(
        (Box, Validator.ONE),
        (Data, Validator.ONE),
    ), doc="""A textual block

    The text to print is contained in child data element.

    """)

Line = Validator(tag="line",
    attributes={
        "pen": (PenType, REQUIRED),
        "color": (Color, REQUIRED),
        "backslant": (Boolean, False),
    }, children=((Box, Validator.ONE),),
    doc="A (straight) line")

Rectangle = Validator(tag="rectangle",
    attributes={
        "pen": (PenType, REQUIRED),
        "pencolor": (Color, REQUIRED),
        "color": (Color, None),
        "radius": (Dimension, 0),
    }, children=((Box, Validator.ONE),), doc="A rectangle")

Image = Validator(tag="image",
    attributes={
        "type": (BitmapType, REQUIRED),
        "file": (String, None),
        "data": (String, None),
        "scale": (Boolean, False),
    }, children=(
        (Box, Validator.ONE),
        (Data, Validator.ZERO_OR_ONE),
    ), doc="""A bitmap image

    The bitmap may be loaded from a file or from a 'data' element
    (either put in the image element or referred by the 'data' attribute.)

    """)

BarCode = Validator(tag="barcode",
    attributes={
        "type": (BarCodeType, REQUIRED),
        "value": (String, REQUIRED),
        "stripes": (String, REQUIRED), # FIXME: must be list of numbers
        "module": (Numeric(1), 10),
        "vertical": (Boolean, False),
    }, children=(
        (Box, Validator.ONE),
    ), doc="""A bar code image

    The data child element contains prebuilt bitmap in png format.

    """)

Outline = Validator(tag="outline",
    validate=Validator.Unique("outline"),
    attributes={
        "name": (String, REQUIRED),
        "title": (String, REQUIRED),
        "level": (Integer, 1),
        "closed": (Boolean, False),
        "x": (Dimension, 0),
        "y": (Dimension, 0),
    },
    doc="A bookmark for document outline navigation"
)

Page = Validator(tag="page",
    attributes={
        "width": (Dimension, REQUIRED),
        "height": (Dimension, REQUIRED),
        "leftmargin": (Dimension, REQUIRED),
        "rightmargin": (Dimension, REQUIRED),
        "topmargin": (Dimension, REQUIRED),
        "bottommargin": (Dimension, REQUIRED),
    }, children=(
        (Text, Validator.UNRESTRICTED),
        (Line, Validator.UNRESTRICTED),
        (Rectangle, Validator.UNRESTRICTED),
        (Image, Validator.UNRESTRICTED),
        (BarCode, Validator.UNRESTRICTED),
        (Outline, Validator.UNRESTRICTED),
    ), doc="Single output page")

def Printout(tree, element, path):
    """Prevalidator for "printout" element: initialize structures"""
    # pylint: disable-msg=W0613
    # W0613: Unused arguments 'element', 'path'

    tree.fonts = {}
    tree.outline = {}
    # Keep the filename if present
    # (repeated validation after the template is loaded)
    if not hasattr(tree, "filename"):
        tree.filename = None

Printout = Validator(tag="printout", prevalidate=Printout,
    attributes={
        "name": (String, None),
        "description": (String, None),
        "version": (String, None),
        "author": (String, None),
        "basedir": (String, None),  # WARNING useless, always None actually
        # TODO: "built": (Timestamp, None),
    }, children=(
        (Font, Validator.ONE_OR_MORE),
        (Data, Validator.UNRESTRICTED),
        (Page, Validator.ONE_OR_MORE),
    ), doc="The root element of printout tree")

def load(source):
    """Load printout file, return ElementTree"""
    _et = ElementTree(Printout)
    _et.parse(source)
    return _et

# vim: set et sts=4 sw=4 :
