"""PythonReports, Python reporting engine

This module provides user interface to PythonReports.
It exports modules, functions and classes needed to
build a report and format or display report printout.

Note: loading all available GUI modules at once
may be convenient but is quite time- and memory-
consuming.  Users are encouraged to import separate
printout rendering modules directly.

"""
"""History:
01-nov-2006 [als]   added API exports
30-jun-2006 [als]   created
"""

__version__ = "$Revision: 1.1 $"[11:-2]
__date__ = "$Date: 2006/11/01 11:00:27 $"[7:-2]

__all__ = [
    "template", "load_template",
    "printout", "load_printout",
    "Builder",
]

from PythonReports import template, printout
from PythonReports.template import load as load_template
from PythonReports.printout import load as load_printout

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

# vim: set et sts=4 sw=4 :
