#! /usr/bin/env python
"""Test building of subreports"""

import sys

from PythonReports.builder import Builder

def run():
    # make some dummy data
    _data = [{
        "item": _ii,
        "sub": [{"item": _jj} for _jj in range(_ii * 10, _ii * 10 + 10)]
    } for _ii in range(10)]
    # create report builder
    _builder = Builder("submain.prt")
    # build printout
    _printout = _builder.run(_data)
    # write printout file
    with open("submain.prp", "wb") as _out:
        _printout.write(_out)

if __name__ == "__main__":
    run()

# vim: set et sts=4 sw=4 :
