#! /usr/bin/env python
"""Test report building"""

"""History (most recent first):
25-jul-2006 [als]   file output adjusted for ElementTree-based API
17-jul-2006 [als]   created
"""

__version__ = "$Revision: 1.1 $"[11:-2]
__date__ = "$Date: 2006/11/01 11:24:31 $"[7:-2]

import sys

from PythonReports.builder import Builder

import sakila

class Progress(object):

    """Progress indicator for report building"""

    BAR_WIDTH = 63

    def __init__(self, builder):
        self.builder = builder
        self.percent = -1

    def __call__(self):
        _context = self.builder.context
        _percent = round((_context["ITEM_NUMBER"] + 1) * 100.0
            / _context["DATA_COUNT"], 1)
        if _percent > self.percent:
            self.percent = _percent
            _pos = int(_percent / 100 * self.BAR_WIDTH)
            sys.stdout.write("\r[%s>%s] %5.1f%%"
                % ("=" * _pos, " " * (self.BAR_WIDTH - _pos), _percent))

def run():
    _builder = Builder("sakila.prt")
    try:
        _printout = _builder.run(sakila.load(),
            item_callback=Progress(_builder))
    except:
        raise
    # end progress report - print newline
    print
    # write printout file
    _out = file("sakila.prp", "w")
    _printout.write(_out)
    _out.close()

if __name__ == "__main__":
    run()

# vim: set et sts=4 sw=4 :
