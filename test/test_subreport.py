#! /usr/bin/env python
"""Test building of subreports"""
"""History (most recent first):
15-dec-2006 [als]   created
"""
__version__ = "$Revision: 1.1 $"[11:-2]
__date__ = "$Date: 2006/12/19 13:25:08 $"[7:-2]

import sys

from PythonReports.builder import Builder

def run():
    # make some dummy data
    _data = [{
        "item": _ii,
        "sub": [{"item": _jj} for _jj in xrange(_ii * 10, _ii * 10 + 10)]
    } for _ii in xrange(10)]
    # create report builder
    _builder = Builder("submain.prt")
    # build printout
    _printout = _builder.run(_data)
    # write printout file
    _out = file("submain.prp", "w")
    _printout.write(_out)
    _out.close()

if __name__ == "__main__":
    run()

# vim: set et sts=4 sw=4 :
