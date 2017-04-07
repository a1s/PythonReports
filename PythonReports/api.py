"""PythonReports Application Program Interface

This module exports modules, functions and classes needed
to build a report and format or display report printout.

"""

__all__ = [
    "template", "load_template",
    "printout", "load_printout",
    "Builder",
]

from PythonReports import template, printout
from PythonReports.template import load as load_template
from PythonReports.printout import load as load_printout
from PythonReports.builder import Builder
from PythonReports.version import *

try:
    from PythonReports import pdf
    from PythonReports.pdf import PdfWriter, write as write_pdf
except ImportError:
    pass
else:
    __all__.extend(("pdf", "PdfWriter", "write_pdf"))

try:
    from PythonReports import Tk
    from PythonReports.Tk import PreviewWidget as TkPreviewWidget
    from PythonReports.Tk import PreviewWindow as TkPreviewWindow
except ImportError:
    pass
else:
    __all__.extend(("Tk", "TkPreviewWidget", "TkPreviewWindow"))

try:
    from PythonReports import wxPrint
    from PythonReports.wxPrint import Printout as wxPrintout
    from PythonReports.wxPrint import Preview as wxPreview
    from PythonReports.wxPrint import PrintApp as wxPrintApp
except ImportError:
    pass
else:
    __all__.extend(("wxPrint", "wxPrintout", "wxPreview", "wxPrintApp"))

try:
    from PythonReports.rson import parse_file as parse_rson
except ImportError:
    pass
else:
    __all__.append("parse_rson")

# vim: set et sts=4 sw=4 :
