"""Migration from PythonReports to s-reports.

PythonReports is superseded by s-reports (https://github.com/a1s/sr.py),
a banded report formatter whose template format follows this one.
This package converts what a PythonReports user has to s-reports:

* `template.convert` turns a template, XML (.prt) or RSON (.prtr),
  into an s-reports template in KDL (.kdl).
* `printout.convert` turns a printout (.prp) into an s-reports printout,
  which s-reports can write as NDJSON or CBOR, or render to PDF.

Both list what they could not carry over unchanged.  The command
line front end is `cli.main`, installed as "pr2sr" and also run
by "python -m PythonReports.migrate".

The template converter needs nothing beyond PythonReports
(and rsonlite for RSON templates).  The printout converter builds
s-reports's own printout model, so it needs the s-reports package.

"""

# vim: set et sts=4 sw=4 :
