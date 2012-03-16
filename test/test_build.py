#! /usr/bin/env python
"""Test report building"""

"""History (most recent first):
01-nov-2006 [als]   initialize wx.App (may be needed for wx backend);
                    add wx-based progress indicator;
                    limit the number of processed rows
25-jul-2006 [als]   file output adjusted for ElementTree-based API
17-jul-2006 [als]   created
"""

__version__ = "$Revision: 1.2 $"[11:-2]
__date__ = "$Date: 2006/11/02 11:30:19 $"[7:-2]

import sys

try:
    import wx
except ImportError:
    wx = None

from PythonReports.builder import Builder

import sakila

# limit the number of data objects to render
# (set to sys.maxint to process the whole sequence).
# (444 doesn't cause page break before the summary section
# with wx and RL drivers and is big enough to see the progress.)
DATA_LIMIT = 444

class Progress(object):

    """Progress indicator for report building"""

    BAR_WIDTH = 63

    def __init__(self, builder):
        self.builder = builder
        self.percent = -1

    def indicate(self):
        """Show progress indicator at self.percent"""
        _pos = int(self.percent / 100 * self.BAR_WIDTH)
        sys.stdout.write("\r[%s>%s] %5.1f%%"
            % ("=" * _pos, " " * (self.BAR_WIDTH - _pos), self.percent))

    def __call__(self):
        _context = self.builder.context
        _percent = round((_context["ITEM_NUMBER"] + 1) * 100.0
            / _context["DATA_COUNT"], 1)
        if _percent > self.percent:
            self.percent = _percent
            self.indicate()

    def terminate(self):
        """Finalize the progress display"""
        print # line feed

if wx:
    class wxProgress(Progress):

        def __init__(self, builder):
            super(wxProgress, self).__init__(builder)
            self.dialog = wx.ProgressDialog("Build Report",
                "Building the report, please wait...",
                style = wx.PD_APP_MODAL | wx.PD_SMOOTH | wx.PD_AUTO_HIDE
                    | wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME)

        def indicate(self):
            self.dialog.Update(self.percent)

        def terminate(self):
            self.dialog.Hide()
            self.dialog.Destroy()

def run():
    if wx:
        # if wx backend is used, App must be created
        # before builder initialization.
        _app = wx.App(0)
    # create report builder
    _builder = Builder("sakila.prt")
    # create progress indicator
    if wx:
        _progress = wxProgress(_builder)
    else:
        _progress = Progress(_builder)
    # build printout
    try:
        _printout = _builder.run(sakila.load()[:DATA_LIMIT],
            item_callback=_progress)
    finally:
        _progress.terminate()
    # write printout file
    _out = file("sakila.prp", "w")
    _printout.write(_out)
    _out.close()

if __name__ == "__main__":
    run()

# vim: set et sts=4 sw=4 :
