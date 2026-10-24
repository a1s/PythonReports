#! /usr/bin/env python
"""Tests of the migration tools: PythonReports to s-reports

Run from this directory with "python test_migrate.py",
or from the top of the source tree with
"python -m unittest discover -s test -p test_migrate.py".
The tests that check results with s-reports, and the printout tests,
are skipped where the s-reports package is not installed;
the RSON test, where rsonlite is not.

"""

import datetime
import io
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
import zlib

from PythonReports.migrate import kdl
from PythonReports.migrate import template
from PythonReports.migrate.expressions import Names, Translator, printf_spec

try:
    from sr.template.load import load_text
except ImportError:
    load_text = None

try:
    import rsonlite
except ImportError:
    rsonlite = None

HERE = os.path.dirname(os.path.abspath(__file__))

def translate(source, deferred=False, **declared):
    """Return the translation of an expression, with names declared."""
    _names = Names()
    _names.parameters = dict((_name, _name)
        for _name in declared.get("parameters", ()))
    _names.variables = dict((_name, _name)
        for _name in declared.get("variables", ()))
    _names.counted = set(declared.get("counted", ()))
    _names.groups = set(declared.get("groups", ()))
    _names.imports = dict(declared.get("imports", {}))
    return Translator(_names).translate(source, deferred)

def flat(text):
    """Return a KDL document with its continued lines joined."""
    return re.sub(r" [\\]\n +", " ", text)

def png(width, height):
    """Return the bytes of a white RGB PNG image."""
    def _chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data \
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    _rows = b"".join(b"\0" + b"\xff" * 3 * width for _row in range(height))
    return b"\x89PNG\r\n\x1a\n" \
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2,
            0, 0, 0)) \
        + _chunk(b"IDAT", zlib.compress(_rows)) + _chunk(b"IEND", b"")

class ExpressionTests(unittest.TestCase):

    """Python expressions into Starlark"""

    def check(self, source, expected, deferred=False, **declared):
        self.assertEqual(translate(source, deferred, **declared).text,
            expected)

    def test_identity(self):
        self.check("float(amount)", "float(amount)")
        self.check("customer['last_name']", "customer['last_name']")

    def test_is_none(self):
        self.check("x is None or y is not None", "x == None or y != None")

    def test_chained_comparison(self):
        self.check("0 < a < 10", "0 < a and a < 10")

    def test_power(self):
        _result = translate("2 ** n")
        self.assertEqual(_result.text, "math.pow(2, n)")
        self.assertTrue(_result.notes)

    def test_item_number_base(self):
        self.check("ITEM_NUMBER", "ITEM_NUMBER - 1")
        self.check("ITEM_NUMBER + 1", "ITEM_NUMBER")
        self.check("ITEM_NUMBER + 3", "ITEM_NUMBER + 2")
        self.check("ITEM_NUMBER * 2", "(ITEM_NUMBER - 1) * 2")

    def test_deferred(self):
        _result = translate("(PAGE_NUMBER, total, customer_COUNT, title, x)",
            True, variables=["total"], groups=["customer"],
            parameters=["title"])
        self.assertEqual(_result.text, "(FINAL.PAGE_NUMBER, FINAL.total, "
            "FINAL.customer_COUNT, title, FINAL.THIS.x)")
        self.assertTrue(_result.final)
        self.assertFalse(translate("title + '!'", True,
            parameters=["title"]).final)
        self.check("VERTICAL_SPACE", "VERTICAL_SPACE", True)

    def test_strftime(self):
        self.check("rental_date.strftime('%d.%m.%Y')",
            "strftime(rental_date, '%d.%m.%Y')")

    def test_field_like_builtin(self):
        self.check("type == 'A'", "THIS.type == 'A'")
        self.check("str(type)", "str(THIS.type)")
        self.check("load", "THIS['load']")

    def test_percent_with_width(self):
        self.check("'%5.2f' % amount", "format('%5.2f', amount)")
        self.check("'%-10s|%3d' % (name, qty)",
            "format('%-10s|%3d', name, qty)")
        self.check("'%s, %s' % (a, b)", "'%s, %s' % (a, b)")

    def test_str_format(self):
        self.check("'{0:.2f} of {1}'.format(a, b)",
            "format('%.2f of %s', a, b)")
        self.check("'{} {}'.format(a, b)", "'{} {}'.format(a, b)")

    def test_fstring(self):
        self.check("f'{a:>8.2f} x'", "format('%8.2f x', a)")

    def test_python_format_builtin(self):
        self.check("format(amount, '.2f')", "format('%.2f', amount)")

    def test_imports(self):
        _imports = {"datetime": "datetime.datetime", "math": "math",
            "Decimal": "decimal.Decimal", "dt": "datetime"}
        self.check("datetime.now()", "BUILD_TIME", imports=_imports)
        self.check("dt.datetime.now()", "BUILD_TIME", imports=_imports)
        self.check("datetime(2005, 1, 2)",
            "time.time(year=2005, month=1, day=2)", imports=_imports)
        self.check("math.floor(x)", "math.floor(x)", imports=_imports)
        self.check("Decimal('1.5')", "decimal('1.5')", imports=_imports)
        self.assertTrue(translate("math.fsum(x)", imports=_imports).notes)

    def test_counted_variable(self):
        self.check("seen", "len(seen)", variables=["seen"], counted=["seen"])

    def test_sets_and_generators(self):
        self.check("{1, 2}", "set([1, 2])")
        self.check("max(x.a for x in items)", "max([x.a for x in items])")

    def test_strings(self):
        self.check("u'caf\\xe9'", "'caf" + chr(0xe9) + "'")
        self.check("'\\x80'", "'\\u0080'")
        self.check("'a\\\\b'", "'a\\\\b'")

    def test_unparsable_source_is_kept(self):
        _result = translate("print >> x")
        self.assertEqual(_result.text, "print >> x")
        _result = translate("a b")
        self.assertEqual(_result.text, "a b")
        self.assertTrue(_result.notes)

    def test_records_are_collected(self):
        _names = Names()
        _translator = Translator(_names)
        _translator.translate("customer.name + strftime_me.strftime('%Y')")
        _translator.translate("items[0]")
        self.assertEqual(_names.records, {"customer": ["object"],
            "strftime_me": ["datetime"], "items": ["list"]})

    def test_printf_spec(self):
        self.assertEqual(printf_spec(">8.2f")[0], "%8.2f")
        self.assertEqual(printf_spec("<10s")[0], "%-10s")
        self.assertEqual(printf_spec("+05d")[0], "%+05d")
        self.assertIsNone(printf_spec("^10")[0])
        self.assertIsNone(printf_spec(",d")[0])

class KdlTests(unittest.TestCase):

    """The KDL writer"""

    def test_quote(self):
        self.assertEqual(kdl.quote("abc"), "\"abc\"")
        self.assertEqual(kdl.quote("a\"b"), "\"a\\\"b\"")
        self.assertEqual(kdl.quote("a\\b"), "#\"a\\b\"#")
        self.assertEqual(kdl.quote("\"#\\"), "##\"\"#\\\"##")
        self.assertEqual(kdl.quote("a\nb"), "\"a\\nb\"")
        self.assertEqual(kdl.quote("a\u200eb"), "\"a\\u{200e}b\"")

    def test_number(self):
        self.assertEqual(kdl.number(1.0), "1")
        self.assertEqual(kdl.number(0.1), "0.1")
        self.assertEqual(kdl.number(-27.346), "-27.346")

    def test_lines_are_wrapped(self):
        _node = kdl.Node("field")
        for _idx in range(12):
            _node.set("property%i" % _idx, "value %i" % _idx)
        _text = kdl.dumps([_node])
        self.assertTrue(all(len(_line) <= 79
            for _line in _text.splitlines()))
        self.assertTrue(_text.splitlines()[0].endswith(" \\"))

GEOMETRY = """<report>
 <font name="f" typeface="Arial" size="10" />
 <layout width="200" height="300" leftmargin="10" rightmargin="10">
  <style font="f" color="black" bgcolor="LIGHTGRAY" />
  <detail>
   <box height="20" />
   <field expr="name"><box x="-51" width="50" /></field>
   <field expr="total" format="%.2f"><box x="5mm" height="7" />
    <style printwhen="total &gt; 0" />
   </field>
   <rectangle pen="0"><box x="10" width="30" /></rectangle>
   <line pen="1"><box y="-1" height="0" /></line>
   <line pen="dot"><box x="5" width="10" height="10" /></line>
  </detail>
 </layout>
</report>
"""

class TemplateTests(unittest.TestCase):

    """Templates into s-reports templates"""

    def setUp(self):
        self.directory = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.directory)

    def write(self, name, text):
        _path = os.path.join(self.directory, name)
        with io.open(_path, "w", encoding="utf-8", newline="\n") as _file:
            _file.write(text)
        return _path

    def validate(self, text, name="test.kdl"):
        """Return the error messages s-reports has about a template."""
        if load_text is None:
            self.skipTest("s-reports is not installed")
        from pathlib import Path
        _loaded = load_text(text, name, Path(self.directory))
        return [str(_item) for _item in _loaded.errors]

    def test_geometry(self):
        _text = flat(template.convert(self.write("g.prt", GEOMETRY)).text)
        self.assertIn("field expr=\"name\" right=0 width=50 "
            "valign=\"bottom\"", _text)
        # Seven points high: one line of 10 point text, as in PythonReports.
        self.assertIn("field expr=\"total\" format=\"%.2f\" left=\"5mm\" "
            "height=12 valign=\"bottom\" printwhen=\"total > 0\"", _text)
        self.assertIn("rectangle stroke=#false left=10 right=140", _text)
        self.assertIn("line width=1 bottom=0 height=0\n", _text)
        self.assertIn("line width=1 dash=\"dot\" backslant=#true left=5 "
            "right=165 height=10", _text)
        self.assertIn("bgcolor=\"#C0C0C0\"", _text)
        self.assertEqual(self.validate(_text), [])

    def test_sakila(self):
        _result = template.convert(os.path.join(HERE, "sakila.prt"))
        _text = flat(_result.text)
        self.assertIn("field expr=\"FINAL.PAGE_NUMBER\" evaltime=\"report\"",
            _text)
        self.assertIn("variable \"report_timestamp\" expr=\"BUILD_TIME\"",
            _text)
        self.assertIn("expr=\"strftime(rental_date, '%d.%m.%Y')\"", _text)
        self.assertIn("printwhen=\"page_amount != None\"", _text)
        self.assertIn("member \"customer\" type=\"object\"", _text)
        self.assertTrue(any("named 'top'" in _note.message
            for _note in _result.notes))
        # The original links to an outline it never names.
        _errors = self.validate(_text)
        self.assertEqual(len(_errors), 1)
        self.assertIn("no outline is named 'top'", _errors[0])

    def test_sample_records(self):
        _records = [{"customer_id": 1, "amount": 2.5,
            "rental_date": "2005-05-24T22:53:30Z", "return_date": None,
            "customer": {"last_name": "SMITH"}, "film": {"title": "A"}}]
        _text = flat(template.convert(os.path.join(HERE, "sakila.prt"),
            _records).text)
        self.assertIn("member \"customer_id\" type=\"int\"", _text)
        self.assertIn("member \"amount\" type=\"float\"", _text)
        self.assertIn("member \"rental_date\" type=\"datetime\"", _text)
        self.assertIn("member \"return_date\" type=\"datetime\" "
            "nullable=#true", _text)

    @unittest.skipIf(rsonlite is None, "rsonlite is not installed")
    def test_sakila_rson(self):
        _text = flat(template.convert(os.path.join(HERE,
            "sakila.prtr")).text)
        self.assertIn("outline title=\"'DVD rental payments'\" "
            "name=\"'top'\" closed=#true", _text)
        self.assertEqual(self.validate(_text), [])

    def test_subreports(self):
        for _name in ("submain.prt", "subsub.prt"):
            shutil.copy(os.path.join(HERE, _name), self.directory)
        _sub = template.convert(os.path.join(self.directory, "subsub.prt"))
        self.write("subsub.kdl", _sub.text)
        _main = template.convert(os.path.join(self.directory, "submain.prt"))
        self.assertEqual(_main.subreports, [("subsub.prt", "subsub.kdl")])
        self.assertIn("subreport seq=-3 embedded=\"loop\" data=\"sub\"",
            _main.text)
        # An embedded subreport runs inline, where a header is a title.
        self.assertIn("embedded \"loop\" {", _main.text)
        self.assertIn("inline=#true", _main.text)
        self.assertIn("header height=7 {", _main.text)
        self.assertTrue(any("page header and footer" in _note.message
            for _note in _main.notes))
        self.assertEqual(self.validate(_sub.text, "subsub.kdl"), [])
        # subsub.prt runs inline and has a header and a footer,
        # which s-reports refuses until they are taken out.
        _errors = self.validate(_main.text, "submain.kdl")
        self.assertTrue(_errors)
        self.assertTrue(all("inline subreport" in _error
            for _error in _errors))

PRINTOUT = """<printout name="test">
 <font name="f" typeface="Arial" size="10" />
 <data name="pic" encoding="base64">%(png)s</data>
 <page width="200" height="300" leftmargin="10" rightmargin="10"
  topmargin="10" bottommargin="10">
  <outline name="o1" title="Top" level="1" x="10" y="10" />
  <outline name="o2" title="Deep" level="3" x="10" y="20" />
  <text font="f" color="#000000" align="right">
   <box x="10" y="30" width="100" height="10" /><data>Hello</data>
  </text>
  <text font="f" color="#000000">
   <box x="10" y="50" width="100" height="22" /><data>two
lines</data>
  </text>
  <line pen="dot" color="#FF0000">
   <box x="10" y="80" width="50" height="20" />
  </line>
  <rectangle pen="0" pencolor="#000000" color="#00FF00">
   <box x="10" y="110" width="20" height="20" />
  </rectangle>
  <image type="png" data="pic">
   <box x="10" y="140" width="10" height="10" />
  </image>
  <barcode type="Code39" value="A" stripes="10,1,1,10" module="10">
   <box x="10" y="160" width="20" height="18" />
  </barcode>
  <xref type="outline" target="o1">
   <box x="100" y="200" width="50" height="20" />
   <text font="f" color="#000000">
    <box x="0" y="5" width="50" height="10" /><data>link</data>
   </text>
  </xref>
 </page>
</printout>
"""

class PrintoutTests(unittest.TestCase):

    """Printouts into s-reports printouts"""

    def setUp(self):
        try:
            from PythonReports.migrate import printout
        except ImportError:
            self.skipTest("s-reports is not installed")
        self.module = printout
        self.directory = tempfile.mkdtemp()
        import base64
        _path = os.path.join(self.directory, "test.prp")
        with io.open(_path, "w", encoding="utf-8", newline="\n") as _file:
            _file.write(PRINTOUT % {"png": base64.b64encode(png(2, 3))
                .decode("ascii")})
        try:
            self.result = printout.convert(_path,
                datetime.datetime(2024, 1, 2, 3, 4, 5))
        except Exception as _error:
            if "font" in str(_error).lower():
                self.skipTest("no font: %s" % _error)
            raise
        self.marks = dict((_mark.kind + str(_idx), _mark) for (_idx, _mark)
            in enumerate(self.result.printout.pages[0].marks))

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_header(self):
        _printout = self.result.printout
        self.assertEqual(_printout.built, "2024-01-02T03:04:05Z")
        self.assertEqual(_printout.report.name, "test")
        self.assertEqual([_font.name for _font in _printout.fonts], ["f"])
        self.assertEqual(list(_printout.data), ["pic"])

    def test_outline_levels(self):
        _outlines = [_mark for _mark in self.result.printout.pages[0].marks
            if _mark.kind == "outline"]
        self.assertEqual([_mark.level for _mark in _outlines], [1, 2])
        # Only a name a link goes to is kept.
        self.assertEqual([_mark.name for _mark in _outlines], ["o1", None])

    def test_text(self):
        _hello = self.marks["text2"]
        self.assertEqual(_hello.lines, ("Hello",))
        self.assertEqual(_hello.align, "right")
        self.assertEqual(_hello.leading, 12)
        self.assertEqual(_hello.box.height, 12)
        self.assertEqual(self.marks["text3"].lines, ("two", "lines"))

    def test_line_and_rectangle(self):
        _line = self.marks["line4"]
        self.assertEqual((_line.width, _line.dash, _line.color), (1, "dot",
            "#FF0000"))
        self.assertTrue(_line.backslant)
        _rectangle = self.marks["rectangle5"]
        self.assertIsNone(_rectangle.stroke)
        self.assertEqual(_rectangle.fill, "#00FF00")

    def test_image_is_cut(self):
        _image = self.marks["image6"]
        self.assertEqual(_image.data, "pic")
        self.assertEqual((_image.box.y, _image.box.width,
            _image.box.height), (147, 2, 3))
        self.assertEqual((_image.crop.width, _image.crop.height), (2, 3))

    def test_barcode(self):
        _barcode = self.marks["barcode7"]
        self.assertEqual(_barcode.module, 0.72)
        self.assertEqual(_barcode.stripes, (10, 1, 1, 10))
        self.assertEqual(_barcode.box.width, 15.84)

    def test_xref(self):
        _xref = self.marks["xref8"]
        self.assertEqual(_xref.target, "o1")
        self.assertEqual(_xref.marks[0].box.x, 100)

    def test_written_and_read(self):
        from pathlib import Path
        from sr.pdf import render
        from sr.printout.read import read
        from sr.printout.write import write_jsonl
        _path = Path(self.directory) / "test.srp.jsonl"
        with _path.open("w", encoding="utf-8", newline="") as _file:
            write_jsonl(self.result.printout, _file, _path.parent)
        _again = read(_path)
        self.assertEqual(len(_again.pages), 1)
        self.assertTrue(render(_again).startswith(b"%PDF"))

if __name__ == "__main__":
    unittest.main()

# vim: set et sts=4 sw=4 :
