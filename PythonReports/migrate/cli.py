"""Command line interface of the migration tools.

Usage::

    pr2sr template [-o OUT] [--records DATA] SOURCE...
    pr2sr printout [-o OUT] [--build-time TIME] SOURCE...

"pr2sr template" converts PythonReports templates, XML or RSON,
into s-reports templates (.kdl).  "pr2sr printout" converts
PythonReports printouts (.prp) into s-reports printouts:
NDJSON (.srp.jsonl), CBOR (.srp.cbor), or PDF rendered by
s-reports (.pdf), chosen by the extension of the output file.

Without -o, each output is written beside its source.  What the
conversion could not carry over unchanged is listed on standard error.
Where s-reports is installed, a converted template is also checked by it,
and the exit status is 1 if s-reports does not accept it as it stands.

"""

__all__ = ["main"]

import argparse
import datetime
import io
import json
import os
import sys

from PythonReports.version import __version__

def main(argv=None):
    """Run the command line, return the exit status."""
    _parser = _make_parser()
    _args = _parser.parse_args(argv)
    if (_args.output is not None) and (len(_args.source) > 1):
        _parser.error("-o takes one source file")
    try:
        return _args.handler(_args)
    except KeyboardInterrupt:
        return 1

def _make_parser():
    """Return the argument parser."""
    _parser = argparse.ArgumentParser(prog="pr2sr",
        description="Convert PythonReports templates and printouts "
            "to s-reports ones.")
    _parser.add_argument("--version", action="version",
        version="%(prog)s " + __version__)
    _commands = _parser.add_subparsers(title="commands", dest="command",
        required=True)
    _template = _commands.add_parser("template",
        help="convert templates (.prt, .prtr) to s-reports templates (.kdl)",
        description="Convert PythonReports templates to s-reports templates.")
    _template.add_argument("source", nargs="+",
        help="template file, XML or RSON")
    _template.add_argument("-o", "--output",
        help="output file; default: the source with .kdl")
    _template.add_argument("--records", metavar="DATA",
        help="sample records, a JSON array or NDJSON, "
            "to choose the types of record fields from")
    _template.set_defaults(handler=_template_command)
    _printout = _commands.add_parser("printout",
        help="convert printouts (.prp) to s-reports printouts or PDF",
        description="Convert PythonReports printouts to s-reports printouts.")
    _printout.add_argument("source", nargs="+", help="printout file")
    _printout.add_argument("-o", "--output",
        help="output file: .srp.jsonl, .srp.cbor, or .pdf; "
            "default: the source with .srp.jsonl")
    _printout.add_argument("--build-time", metavar="TIME",
        help="RFC 3339 time to record as the build time; "
            "default: when the source was last modified")
    _printout.set_defaults(handler=_printout_command)
    return _parser

def _report(source, message):
    """Write one line about a source file to standard error."""
    sys.stderr.write("%s: %s\n" % (source, message))

def _target(source, output, extension):
    """Return the output path for a source file."""
    if output is not None:
        return output
    (_stem, _ext) = os.path.splitext(source)
    if _ext.lower() not in (".prt", ".prtr", ".xml", ".prp"):
        _stem = source
    return _stem + extension

def _unique(source, target, written):
    """Return False if an earlier source of this run went to the target.

    Parameters:
        source: the source file.
        target: the file it would be written to.
        written: dictionary of the targets so far, mapped to their sources.

    """
    _key = os.path.normcase(os.path.abspath(target))
    if _key in written:
        _report(source, "not converted: %s would overwrite the conversion "
            "of %s; give it -o" % (target, written[_key]))
        return False
    written[_key] = source
    return True

def _load_records(path):
    """Return the records of a JSON array or NDJSON file."""
    with io.open(path, encoding="utf-8-sig") as _file:
        _text = _file.read()
    _stripped = _text.lstrip()
    if _stripped.startswith("["):
        return json.loads(_text)
    return [json.loads(_line) for _line in _text.splitlines()
        if _line.strip()]

def _template_command(args):
    """Convert templates."""
    from PythonReports.migrate.template import convert
    _records = None
    if args.records:
        try:
            _records = _load_records(args.records)
        except (OSError, ValueError) as _error:
            _report(args.records, "cannot read the records: %s" % _error)
            return 1
    _status = 0
    _written = {}
    for _source in args.source:
        _out = _target(_source, args.output, ".kdl")
        if not _unique(_source, _out, _written):
            _status = 1
            continue
        try:
            _result = convert(_source, _records)
        except Exception as _error:
            _report(_source, "not converted: %s" % _error)
            _status = 1
            continue
        with io.open(_out, "w", encoding="utf-8", newline="\n") as _file:
            _file.write(_result.text)
        _report(_source, "written to %s" % _out)
        for _note in _result.notes:
            _report(_source, str(_note))
        if not _validate(_out):
            _status = 1
    return _status

def _validate(path):
    """Check a converted template with s-reports, where it is installed.

    Return False if s-reports refuses the template.

    """
    try:
        from sr.template.load import load
    except ImportError:
        return True
    _loaded = load(path)
    for _item in _loaded.errors:
        _report(path, "s-reports: error: %s" % _item)
    for _item in _loaded.warnings:
        _report(path, "s-reports: warning: %s" % _item)
    return _loaded.ok

def _printout_command(args):
    """Convert printouts."""
    try:
        from PythonReports.migrate.printout import convert
    except ImportError as _error:
        sys.stderr.write("pr2sr printout needs s-reports: "
            "pip install s-reports (%s)\n" % _error)
        return 1
    _built = None
    if args.build_time:
        try:
            _built = datetime.datetime.fromisoformat(
                args.build_time.replace("Z", "+00:00"))
        except ValueError:
            sys.stderr.write("--build-time: not an RFC 3339 time: %s\n"
                % args.build_time)
            return 2
    _status = 0
    _written = {}
    for _source in args.source:
        _out = _target(_source, args.output, ".srp.jsonl")
        if not _unique(_source, _out, _written):
            _status = 1
            continue
        try:
            _result = convert(_source, _built)
            _write_printout(_result.printout, _out)
        except Exception as _error:
            _report(_source, "not converted: %s" % _error)
            _status = 1
            continue
        _report(_source, "written to %s" % _out)
        for _note in _result.notes:
            _report(_source, _note)
    return _status

def _write_printout(printout, path):
    """Write an s-reports printout in the format the file extension names."""
    from pathlib import Path
    _path = Path(path)
    _name = _path.name.lower()
    if _name.endswith(".pdf"):
        from sr.pdf import render
        _path.write_bytes(render(printout))
    elif _name.endswith(".cbor"):
        from sr.printout.write import write_cbor
        with _path.open("wb") as _file:
            write_cbor(printout, _file, _path.parent)
    else:
        from sr.printout.write import write_jsonl
        with _path.open("w", encoding="utf-8", newline="") as _file:
            write_jsonl(printout, _file, _path.parent)

if __name__ == "__main__":
    sys.exit(main())

# vim: set et sts=4 sw=4 :
