"""Translate PythonReports expressions into s-reports expressions.

PythonReports evaluates template expressions as Python,
with the names of the report in scope.  s-reports evaluates them
as Starlark: a language that reads like Python but has no imports,
no ``**``, no ``is``, no lambdas, and a smaller set of builtins.
The two engines also look names up in a different order, and a few
of the names they share do not mean quite the same thing.

Each expression is parsed with Python's own parser, the tree is
rewritten, and the result is written back as Starlark.  What changes:

* ``ITEM_NUMBER`` counts from 0 in PythonReports and from 1 in s-reports,
  so it becomes ``(ITEM_NUMBER - 1)``.
* A record field whose name s-reports gives to a builtin, a module,
  or a predefined variable is reached through ``THIS``: in PythonReports
  the field hides the builtin, and in s-reports the builtin hides the field.
* An expression with ``evaltime`` is evaluated at the end of its scope
  in PythonReports.  In s-reports only names read through ``FINAL`` are,
  so every name that changes as the report is built gets that prefix.
* ``is`` and ``is not`` become ``==`` and ``!=``, a chained comparison
  becomes a conjunction, ``a ** b`` becomes ``math.pow(a, b)``, a set
  literal becomes ``set([...])``, and a generator a list comprehension.
* ``x.strftime(spec)`` becomes ``strftime(x, spec)``, and the clock,
  ``datetime.now()``, becomes ``BUILD_TIME``.
* ``%`` formats, ``str.format`` fields, and f-strings that use flags,
  a width, or a precision become calls to s-reports's ``format`` builtin,
  since Starlark's own ``%`` takes none of them.

Whatever has no counterpart is left as it was written and reported
in a note, so that the converted template says where it needs work.

"""

__all__ = ["Names", "Translation", "Translator", "printf_spec",
    "starlark", "starlark_string"]

import ast
import builtins
import re
import string

# Predefined variables of PythonReports.  Every group adds two more.
PREDEFINED = ("THIS", "ITEM_NUMBER", "DATA_COUNT", "REPORT_COUNT",
    "PAGE_COUNT", "COLUMN_COUNT", "PAGE_NUMBER", "COLUMN_NUMBER",
    "VERTICAL_POSITION", "VERTICAL_SPACE")

# Predefined variables that s-reports does not keep in FINAL:
# they describe a band being measured, and no band is at the end of a scope.
UNFINAL = ("VERTICAL_POSITION", "VERTICAL_SPACE")

# Names s-reports resolves ahead of record fields, beyond PythonReports' own.
SR_PREDEFINED = PREDEFINED + ("BUILD_TIME", "FINAL")

# The global names of s-reports expressions: Starlark builtins,
# the two modules, and the engine's own functions.
SR_GLOBALS = frozenset(("abs", "all", "any", "bool", "bytes", "chr",
    "decimal", "dict", "dir", "enumerate", "fail", "float", "format",
    "getattr", "hasattr", "hash", "int", "len", "list", "math", "max",
    "min", "ord", "quantize", "range", "repr", "reversed", "round", "set",
    "sorted", "str", "strftime", "time", "tuple", "type", "zip"))

# What s-reports's math module holds.
SR_MATH = frozenset(("ceil", "floor", "round", "mod", "pow", "sqrt",
    "fabs", "exp", "log", "hypot", "copysign", "remainder", "sin", "cos",
    "tan", "asin", "acos", "atan", "atan2", "sinh", "cosh", "tanh", "asinh",
    "acosh", "atanh", "degrees", "radians", "gamma", "pi", "e"))

# Starlark reserves these, so none of them can be a bare name there.
STARLARK_KEYWORDS = frozenset(("and", "break", "continue", "def", "elif",
    "else", "for", "if", "in", "lambda", "load", "not", "or", "pass",
    "return", "as", "assert", "async", "await", "class", "del", "except",
    "finally", "from", "global", "import", "is", "nonlocal", "raise", "try",
    "while", "with", "yield"))

# Python builtins, including the ones Python 2 had: templates written
# for PythonReports under Python 2 may still call them.
PY_BUILTINS = frozenset(dir(builtins)) | frozenset(("unicode", "long",
    "basestring", "xrange", "cmp", "reduce", "unichr", "file", "apply",
    "raw_input", "execfile", "buffer", "coerce", "intern"))

# Python builtins with a different name, or no name at all, in s-reports.
_RENAMED_BUILTINS = {
    "unicode": "str",
    "long": "int",
    "xrange": "range",
    "unichr": "chr",
    "frozenset": "set",
}

# Attributes of a datetime value, which hint at a record field's type.
_TIME_ATTRIBUTES = frozenset(("year", "month", "day", "hour", "minute",
    "second", "microsecond", "date", "time", "weekday", "isoweekday",
    "isoformat", "strftime", "timetuple", "toordinal"))

# String methods Python has and Starlark does not.
_PY_STRING_METHODS = frozenset(("center", "ljust", "rjust", "zfill",
    "encode", "decode", "expandtabs", "casefold", "swapcase", "translate",
    "maketrans", "format_map", "isdecimal", "isnumeric", "isidentifier",
    "isprintable", "isascii", "has_key", "iteritems", "iterkeys",
    "itervalues"))

# A % conversion: an optional mapping key, flags, width, precision,
# an optional length modifier, and the conversion letter.
CONVERSION = re.compile(r"%(?:\((?P<key>[^)]*)\))?(?P<flags>[-+ #0]*)"
    r"(?P<width>\*|\d+)?(?:\.(?P<precision>\*|\d*))?[hlL]?(?P<verb>.)",
    re.DOTALL)

# Conversions Starlark's own % takes, with no flags, width or precision.
_STARLARK_VERBS = frozenset("srdioxXefgEGc%")

# Conversions s-reports's format builtin takes, and what Python's become.
_ENGINE_VERBS = frozenset("sqdioxXbeEfgGc%")
_VERB_SPELLINGS = {"u": "d", "F": "f", "r": "q", "a": "q"}

# The format specification mini-language of str.format and f-strings.
_FORMAT_SPEC = re.compile(r"^(?:(?P<fill>.)?(?P<align>[<>=^]))?"
    r"(?P<sign>[-+ ])?(?P<z>z)?(?P<alt>#)?(?P<zero>0)?(?P<width>\d+)?"
    r"(?P<group>[,_])?(?:\.(?P<precision>\d+))?(?P<kind>[bcdeEfFgGnosxX%])?$",
    re.DOTALL)

# Operator precedence of Starlark, loosest first.
(LAMBDA, IFEXP, OR, AND, NOT, COMPARE, BIT_OR, BIT_XOR, BIT_AND, SHIFT,
    ARITH, TERM, UNARY, POWER, PRIMARY, ATOM) = range(1, 17)

_BINARY = {
    ast.Add: ("+", ARITH),
    ast.Sub: ("-", ARITH),
    ast.Mult: ("*", TERM),
    ast.Div: ("/", TERM),
    ast.FloorDiv: ("//", TERM),
    ast.Mod: ("%", TERM),
    ast.MatMult: ("@", TERM),
    ast.LShift: ("<<", SHIFT),
    ast.RShift: (">>", SHIFT),
    ast.BitOr: ("|", BIT_OR),
    ast.BitXor: ("^", BIT_XOR),
    ast.BitAnd: ("&", BIT_AND),
    ast.Pow: ("**", POWER),
}

_UNARY = {
    ast.UAdd: "+",
    ast.USub: "-",
    ast.Invert: "~",
}

_COMPARE = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.In: "in",
    ast.NotIn: "not in",
    ast.Is: "is",
    ast.IsNot: "is not",
}

class Names(object):

    """What a template declares, as its expressions see it

    One object is kept for each layout with names of its own: the report,
    and each embedded subreport.  The translator fills `records` with every
    record field the expressions read, in the order they are met.

    Attributes:
        parameters: parameter names, mapped to the name s-reports uses.
        variables: variable names, mapped to the name s-reports uses.
        counted: variables whose "count" became a set in s-reports,
            so that reading one reads its length.
        groups: group names.
        imports: names created by import elements, mapped to the
            dotted path they import.
        records: record field names, mapped to a list of hints about
            the field's type: "object", "list", "datetime".

    """

    def __init__(self):
        self.parameters = {}
        self.variables = {}
        self.counted = set()
        self.groups = set()
        self.imports = {}
        self.records = {}

    def is_predefined(self, name):
        """Return True if the name is a predefined variable."""
        if name in PREDEFINED:
            return True
        for _suffix in ("_COUNT", "_PAGE_NUMBER"):
            if name.endswith(_suffix) \
            and (name[:-len(_suffix)] in self.groups):
                return True
        return False

    def reserved(self, name):
        """Return True if s-reports resolves the name before record fields."""
        return (name in SR_PREDEFINED) or (name in SR_GLOBALS) \
            or self.is_predefined(name) or name.startswith("_sr_") \
            or (name in self.parameters.values()) \
            or (name in self.variables.values())

    def hint(self, name, kind=None):
        """Register a record field, with an optional hint of its type."""
        _hints = self.records.setdefault(name, [])
        if kind and (kind not in _hints):
            _hints.append(kind)

class Translation(object):

    """One translated expression

    Attributes:
        source: the expression as PythonReports had it.
        tree: the rewritten tree, or None if the source did not parse.
        text: the expression as s-reports should have it.
        notes: what could not be translated, or changed meaning.
        final: True if the result reads a name through FINAL.

    """

    def __init__(self, source, tree, notes, final):
        self.source = source
        self.tree = tree
        self.notes = notes
        self.final = final
        self.text = source if tree is None else starlark(tree)

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.text)

class Translator(object):

    """Translate the expressions of one layout"""

    def __init__(self, names):
        """Create a translator for the names of one layout.

        Parameters:
            names: Names object for the layout.  Record fields met
                by the translation are added to it.

        """
        self.names = names

    def translate(self, source, deferred=False, hint=None):
        """Return a Translation of one expression.

        Parameters:
            source: the expression text.
            deferred: True if the expression belongs to an element
                with "evaltime", and must read the end of its scope.
            hint: a type hint for a record field that makes up
                the whole expression, such as "list" for the data
                of a subreport.

        """
        _text = source.strip()
        _tree = _parse(_text)
        if _tree is None:
            return Translation(source, None, [
                "the expression does not parse as Python, "
                "so it is copied unchanged"], False)
        if hint and isinstance(_tree, ast.Name):
            _kind = _Rewriter(self.names, False).kind(_tree.id)
            if _kind == "record":
                self.names.hint(_tree.id, hint)
        _rewriter = _Rewriter(self.names, deferred)
        _tree = _rewriter.visit(_tree)
        ast.fix_missing_locations(_tree)
        return Translation(source, _tree, _rewriter.notes, _rewriter.final)

def _parse(text):
    """Return the expression tree of a source text, or None."""
    for _candidate in (text, "(%s)" % text):
        try:
            return ast.parse(_candidate, mode="eval").body
        except SyntaxError:
            continue
        except ValueError:
            # A null character, which no expression should hold.
            return None
    return None

def _name(identifier):
    """Return a Name node that reads an identifier."""
    return ast.Name(id=identifier, ctx=ast.Load())

def _attribute(base, attr):
    """Return an Attribute node, or a subscript where attr is no name."""
    if attr.isidentifier() and (attr not in STARLARK_KEYWORDS):
        return ast.Attribute(value=base, attr=attr, ctx=ast.Load())
    return ast.Subscript(value=base, slice=ast.Constant(value=attr),
        ctx=ast.Load())

def _call(func, args=(), keywords=()):
    """Return a Call node."""
    if isinstance(func, str):
        func = _name(func)
    return ast.Call(func=func, args=list(args), keywords=list(keywords))

def _dotted(node):
    """Return the dotted name an Attribute chain spells, or None."""
    _parts = []
    while isinstance(node, ast.Attribute):
        _parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    _parts.append(node.id)
    return ".".join(reversed(_parts))

class _Rewriter(ast.NodeTransformer):

    """The rewriting pass of one expression"""

    def __init__(self, names, deferred):
        super().__init__()
        self.names = names
        self.deferred = deferred
        self.notes = []
        self.final = False
        # Names bound by comprehensions and lambdas, innermost last.
        self.bound = []
        # True while visiting an argument that takes a function,
        # as in sorted(items, key=len): a builtin named there
        # is the builtin, and not a record field of that name.
        self.function_value = False

    def note(self, text):
        """Record a note once."""
        if text not in self.notes:
            self.notes.append(text)

    def kind(self, name, called=False):
        """Return what a name refers to, as PythonReports looks it up."""
        if any(name in _scope for _scope in self.bound):
            return "bound"
        if self.names.is_predefined(name):
            return "predefined"
        if name in self.names.imports:
            return "import"
        if name in self.names.parameters:
            return "parameter"
        if name in self.names.variables:
            return "variable"
        if (name in PY_BUILTINS) and (called or self.function_value):
            return "builtin"
        return "record"

    def finally_(self, name):
        """Return a node reading a name at the end of the scope."""
        self.final = True
        return _attribute(_name("FINAL"), name)

    # -- names -----------------------------------------------------------

    def visit_Name(self, node):
        """Rewrite a name by what it refers to."""
        if not isinstance(node.ctx, ast.Load):
            return node
        _id = node.id
        _kind = self.kind(_id)
        if _kind == "predefined":
            if self.deferred and (_id not in UNFINAL):
                _rv = self.finally_(_id)
            else:
                _rv = node
            if _id == "ITEM_NUMBER":
                _rv = ast.BinOp(left=_rv, op=ast.Sub(),
                    right=ast.Constant(value=1))
                _rv.item_number = True
            return _rv
        if _kind == "import":
            return self.imported_value(node)
        if _kind == "parameter":
            return _name(self.names.parameters[_id])
        if _kind == "variable":
            _new = self.names.variables[_id]
            _rv = self.finally_(_new) if self.deferred else _name(_new)
            if _id in self.names.counted:
                _rv = _call("len", [_rv])
            return _rv
        if _kind == "builtin":
            if (_id not in SR_GLOBALS) and (_id not in _RENAMED_BUILTINS):
                self.note("%s is not available in s-reports" % _id)
            return _name(_RENAMED_BUILTINS.get(_id, _id))
        if _kind == "record":
            return self.record(_id)
        return node

    def record(self, field):
        """Return a node reading a record field."""
        self.names.hint(field)
        if self.deferred:
            return _attribute(self.finally_("THIS"), field)
        if self.names.reserved(field) or (field in STARLARK_KEYWORDS) \
        or not field.isidentifier():
            return _attribute(_name("THIS"), field)
        return _name(field)

    def is_record(self, node):
        """Return True if the node is a bare name of a record field."""
        return isinstance(node, ast.Name) and (self.kind(node.id) == "record")

    def is_this(self, node):
        """Return True if the node reads THIS."""
        return isinstance(node, ast.Name) and (node.id == "THIS") \
            and (self.kind("THIS") == "predefined")

    def visit_Attribute(self, node):
        """Rewrite an attribute, noting what it says of a record field."""
        _base = node.value
        if self.is_imported(node):
            return self.imported_value(node)
        if self.is_record(_base):
            self.names.hint(_base.id, "datetime"
                if node.attr in _TIME_ATTRIBUTES else "object")
        elif self.is_this(_base):
            self.names.hint(node.attr)
        if node.attr == "microsecond":
            self.note("time values in s-reports have .nanosecond "
                "rather than .microsecond")
        return self.generic_visit(node)

    def visit_Subscript(self, node):
        """Rewrite a subscript, noting what it says of a record field."""
        _base = node.value
        _index = node.slice
        if self.is_record(_base):
            if isinstance(_index, ast.Constant) \
            and isinstance(_index.value, int):
                self.names.hint(_base.id, "list")
            elif not isinstance(_index, ast.Slice):
                self.names.hint(_base.id, "object")
        elif self.is_this(_base) and isinstance(_index, ast.Constant) \
        and isinstance(_index.value, str):
            self.names.hint(_index.value)
        return self.generic_visit(node)

    # -- scopes of their own ---------------------------------------------

    def comprehension(self, node):
        """Visit a comprehension with its targets bound."""
        _bound = set()
        for _generator in node.generators:
            for _target in ast.walk(_generator.target):
                if isinstance(_target, ast.Name):
                    _bound.add(_target.id)
        self.bound.append(_bound)
        try:
            return self.generic_visit(node)
        finally:
            self.bound.pop()

    def visit_ListComp(self, node):
        """Rewrite a list comprehension."""
        return self.comprehension(node)

    def visit_DictComp(self, node):
        """Rewrite a dict comprehension."""
        return self.comprehension(node)

    def visit_SetComp(self, node):
        """Rewrite a set comprehension as set() of a list one."""
        node = self.comprehension(node)
        return _call("set", [ast.ListComp(elt=node.elt,
            generators=node.generators)])

    def visit_GeneratorExp(self, node):
        """Rewrite a generator expression as a list comprehension."""
        node = self.comprehension(node)
        return ast.ListComp(elt=node.elt, generators=node.generators)

    def visit_Lambda(self, node):
        """Note a lambda, which s-reports has not got."""
        self.note("s-reports expressions have no lambdas")
        _bound = set(_arg.arg for _arg in node.args.args)
        self.bound.append(_bound)
        try:
            return self.generic_visit(node)
        finally:
            self.bound.pop()

    # -- syntax Starlark has not got -------------------------------------

    def visit_Compare(self, node):
        """Rewrite is, is not, and chained comparisons."""
        node = self.generic_visit(node)
        _ops = []
        for _op in node.ops:
            if isinstance(_op, ast.Is):
                _op = ast.Eq()
            elif isinstance(_op, ast.IsNot):
                _op = ast.NotEq()
            _ops.append(_op)
        if len(_ops) == 1:
            return ast.Compare(left=node.left, ops=_ops,
                comparators=node.comparators)
        # A chained comparison is a conjunction of its links.
        _operands = [node.left] + list(node.comparators)
        return ast.BoolOp(op=ast.And(), values=[
            ast.Compare(left=_operands[_idx], ops=[_op],
                comparators=[_operands[_idx + 1]])
            for (_idx, _op) in enumerate(_ops)])

    def visit_BinOp(self, node):
        """Rewrite ** and % formats, and fold ITEM_NUMBER offsets."""
        node = self.generic_visit(node)
        _left = node.left
        if getattr(_left, "item_number", False) \
        and isinstance(node.op, (ast.Add, ast.Sub)) \
        and isinstance(node.right, ast.Constant) \
        and isinstance(node.right.value, int) \
        and not isinstance(node.right.value, bool):
            # ITEM_NUMBER + 1 was the 1-based number; s-reports's is that.
            _offset = -1 + (node.right.value
                if isinstance(node.op, ast.Add) else -node.right.value)
            if _offset == 0:
                return _left.left
            return ast.BinOp(left=_left.left,
                op=ast.Add() if _offset > 0 else ast.Sub(),
                right=ast.Constant(value=abs(_offset)))
        if isinstance(node.op, ast.Pow):
            self.note("a ** b became math.pow(a, b), which gives a float")
            return _call(_attribute(_name("math"), "pow"),
                [node.left, node.right])
        if isinstance(node.op, ast.MatMult):
            self.note("s-reports has no @ operator")
        if isinstance(node.op, ast.Mod) \
        and isinstance(node.left, ast.Constant) \
        and isinstance(node.left.value, str):
            return self.percent(node)
        return node

    def percent(self, node):
        """Rewrite a % format that Starlark's own % cannot apply."""
        _spec = node.left.value
        _conversions = list(CONVERSION.finditer(_spec))
        _plain = all(not (_item.group("flags") or _item.group("width")
            or (_item.group("precision") is not None))
            and (_item.group("verb") in _STARLARK_VERBS)
            for _item in _conversions)
        if _plain:
            return node
        if any(_item.group("key") is not None for _item in _conversions):
            self.note("a %(name) format with flags, width or precision "
                "has no counterpart in s-reports")
            return node
        (_engine, _notes) = engine_format(_spec)
        for _text in _notes:
            self.note(_text)
        if _engine is None:
            return node
        _count = len([_item for _item in _conversions
            if _item.group("verb") != "%"])
        if isinstance(node.right, ast.Tuple) and not any(
            isinstance(_item, ast.Starred) for _item in node.right.elts
        ):
            _args = list(node.right.elts)
        elif _count == 1:
            _args = [node.right]
        else:
            self.note("this %% format needs s-reports's format() builtin, "
                "and its values are not written out as a tuple")
            return node
        return _call("format", [ast.Constant(value=_engine)] + _args)

    def visit_Set(self, node):
        """Rewrite a set literal as set() of a list."""
        node = self.generic_visit(node)
        return _call("set", [ast.List(elts=node.elts, ctx=ast.Load())])

    def visit_NamedExpr(self, node):
        """Note :=, which s-reports has not got."""
        self.note("s-reports has no := operator")
        return self.generic_visit(node)

    def visit_Starred(self, node):
        """Note a starred argument, which s-reports has not got."""
        self.note("s-reports takes no starred arguments")
        return self.generic_visit(node)

    def visit_Dict(self, node):
        """Note ** in a dict, which s-reports has not got."""
        if any(_key is None for _key in node.keys):
            self.note("s-reports cannot unpack a dict with **")
        return self.generic_visit(node)

    def visit_Constant(self, node):
        """Note a constant of a type s-reports has not got."""
        if isinstance(node.value, complex):
            self.note("s-reports has no complex numbers")
        elif node.value is Ellipsis:
            self.note("s-reports has no Ellipsis")
        return node

    def visit_JoinedStr(self, node):
        """Rewrite an f-string as a call to s-reports's format."""
        _parts = []
        _args = []
        for _value in node.values:
            if isinstance(_value, ast.Constant):
                _parts.append(_value.value.replace("%", "%%"))
                continue
            _spec = ""
            if _value.format_spec is not None:
                if not all(isinstance(_item, ast.Constant)
                    for _item in _value.format_spec.values
                ):
                    self.note("an f-string with a computed format "
                        "specification has no counterpart in s-reports")
                    return self.generic_visit(node)
                _spec = "".join(_item.value
                    for _item in _value.format_spec.values)
            _conversion = chr(_value.conversion) \
                if _value.conversion > 0 else None
            (_printf, _notes) = printf_spec(_spec, _conversion)
            for _text in _notes:
                self.note(_text)
            if _printf is None:
                self.note("the f-string format {%s} has no counterpart "
                    "in s-reports" % _spec)
                return self.generic_visit(node)
            _parts.append(_printf)
            _args.append(self.visit(_value.value))
        if not _args:
            return ast.Constant(value="".join(_parts).replace("%%", "%"))
        return _call("format", [ast.Constant(value="".join(_parts))] + _args)

    # -- calls -----------------------------------------------------------

    def is_imported(self, node):
        """Return True if a name or an attribute chain starts at an import."""
        _dotted_name = _dotted(node)
        return (_dotted_name is not None) \
            and (self.kind(_dotted_name.split(".", 1)[0]) == "import")

    def visit_Call(self, node):
        """Rewrite a call: methods, builtins, and imported functions."""
        _func = node.func
        if self.is_imported(_func):
            return self.imported_call(node)
        if isinstance(_func, ast.Attribute):
            _base = _func.value
            if _func.attr == "strftime":
                if self.is_record(_base):
                    self.names.hint(_base.id, "datetime")
                (_args, _keywords) = self.arguments_of(node)
                return _call("strftime", [self.visit(_base)] + _args,
                    _keywords)
            if (_func.attr == "format") and isinstance(_base, ast.Constant) \
            and isinstance(_base.value, str):
                return self.str_format(node)
            if _func.attr in _PY_STRING_METHODS:
                self.note("the .%s() method is not available in s-reports"
                    % _func.attr)
            elif _func.attr in ("isoformat", "date", "timetuple",
                "weekday", "isoweekday", "toordinal", "replace"
            ) and self.is_record(_base):
                self.names.hint(_base.id, "datetime")
                if _func.attr != "replace":
                    self.note("time values in s-reports have no .%s() method; "
                        "see strftime() and .format()" % _func.attr)
        elif isinstance(_func, ast.Name) \
        and (self.kind(_func.id, called=True) == "builtin"):
            return self.builtin_call(node)
        _new_func = self.visit(_func)
        (_args, _keywords) = self.arguments_of(node)
        return ast.Call(func=_new_func, args=_args, keywords=_keywords)

    def arguments_of(self, node):
        """Return the visited positional and keyword arguments of a call."""
        _takes_function = isinstance(node.func, ast.Name) \
            and (node.func.id in ("map", "filter", "reduce", "apply"))
        _args = []
        for (_idx, _arg) in enumerate(node.args):
            _args.append(self.function_argument(_arg)
                if _takes_function and (_idx == 0) else self.visit(_arg))
        _keywords = []
        for _keyword in node.keywords:
            if _keyword.arg is None:
                self.note("s-reports takes no ** arguments")
            _keywords.append(ast.keyword(arg=_keyword.arg,
                value=self.function_argument(_keyword.value)))
        return (_args, _keywords)

    def function_argument(self, node):
        """Visit an argument that may be a function, such as key=len."""
        if not isinstance(node, ast.Name):
            return self.visit(node)
        _outer = self.function_value
        self.function_value = True
        try:
            return self.visit(node)
        finally:
            self.function_value = _outer

    def builtin_call(self, node):
        """Rewrite a call to a Python builtin."""
        _id = node.func.id
        (_args, _keywords) = self.arguments_of(node)
        if _id in _RENAMED_BUILTINS:
            return _call(_RENAMED_BUILTINS[_id], _args, _keywords)
        if (_id == "pow") and (len(_args) == 2):
            self.note("pow(a, b) became math.pow(a, b), which gives a float")
            return _call(_attribute(_name("math"), "pow"), _args)
        if _id == "format":
            return self.format_call(node, _args)
        if (_id == "round") and (len(_args) > 1):
            self.note("round() takes one argument in s-reports: use"
                " quantize() for a decimal, or the format property for text")
        elif (_id == "sorted") and any(_item.arg == "cmp"
            for _item in _keywords
        ):
            self.note("sorted() takes key= in s-reports, not cmp=")
        elif _id == "type":
            self.note("type() gives the name of a type in s-reports")
        elif _id not in SR_GLOBALS:
            self.note("%s() is not available in s-reports" % _id)
        return _call(_id, _args, _keywords)

    def format_call(self, node, args):
        """Rewrite Python's format(value, spec) as s-reports's format."""
        if len(args) == 1:
            return _call("str", args)
        if (len(args) == 2) and isinstance(node.args[1], ast.Constant) \
        and isinstance(node.args[1].value, str):
            (_printf, _notes) = printf_spec(node.args[1].value)
            for _text in _notes:
                self.note(_text)
            if _printf is not None:
                return _call("format",
                    [ast.Constant(value=_printf), args[0]])
        self.note("format(value, spec) has its arguments the other way "
            "round in s-reports: format(spec, value), with a % specification")
        return _call("format", args)

    def str_format(self, node):
        """Rewrite "...".format() where a field has a specification."""
        _template = node.func.value.value
        (_args, _keywords) = self.arguments_of(node)
        try:
            _fields = list(string.Formatter().parse(_template))
        except ValueError:
            self.note("the format string does not parse")
            return ast.Call(func=node.func, args=_args, keywords=_keywords)
        if all(not (_spec or _conversion)
            for (_text, _field, _spec, _conversion) in _fields
        ):
            return ast.Call(func=node.func, args=_args, keywords=_keywords)
        _named = dict((_item.arg, _item.value) for _item in _keywords)
        _parts = []
        _values = []
        _auto = 0
        for (_text, _field, _spec, _conversion) in _fields:
            _parts.append(_text.replace("%", "%%"))
            if _field is None:
                continue
            if _field == "":
                _key = _auto
                _auto += 1
            elif _field.isdigit():
                _key = int(_field)
            elif _field.isidentifier():
                _key = _field
            else:
                self.note("the format field {%s} has no counterpart "
                    "in s-reports" % _field)
                return ast.Call(func=node.func, args=_args, keywords=_keywords)
            try:
                _values.append(_named[_key] if isinstance(_key, str)
                    else _args[_key])
            except (KeyError, IndexError):
                self.note("the format field {%s} has no value" % _field)
                return ast.Call(func=node.func, args=_args, keywords=_keywords)
            (_printf, _notes) = printf_spec(_spec or "", _conversion)
            for _note in _notes:
                self.note(_note)
            if _printf is None:
                self.note("the format specification {%s:%s} has no "
                    "counterpart in s-reports" % (_field, _spec))
                return ast.Call(func=node.func, args=_args, keywords=_keywords)
            _parts.append(_printf)
        return _call("format", [ast.Constant(value="".join(_parts))]
            + _values)

    # -- imports ---------------------------------------------------------

    def qualified(self, node):
        """Return the dotted path a reference to an import names."""
        _dotted_name = _dotted(node)
        if _dotted_name is None:
            return None
        _parts = _dotted_name.split(".")
        _path = self.names.imports.get(_parts[0])
        if _path is None:
            return None
        return ".".join([_path] + _parts[1:])

    def imported_value(self, node):
        """Rewrite a value read from an imported module."""
        _path = self.qualified(node)
        if _path and _path.startswith("math."):
            _member = _path[5:]
            if _member in SR_MATH:
                return _attribute(_name("math"), _member)
        self.note("%s comes from an import, which s-reports has"
            " no counterpart for" % (_path or _dotted(node)))
        return node

    def imported_call(self, node):
        """Rewrite a call to something an import element named."""
        _path = self.qualified(node.func)
        (_args, _keywords) = self.arguments_of(node)
        if _path in ("datetime.datetime.now", "datetime.datetime.today",
            "datetime.datetime.utcnow", "datetime.date.today",
            "time.localtime", "time.gmtime",
        ):
            self.note("s-reports expressions have no clock; "
                "BUILD_TIME, the time the report is built, stands in")
            return _name("BUILD_TIME")
        if _path == "time.time":
            self.note("s-reports expressions have no clock; "
                "BUILD_TIME, the time the report is built, stands in")
            return _call("float",
                [_attribute(_name("BUILD_TIME"), "unix")])
        if (_path == "time.strftime") and (len(_args) == 1):
            self.note("s-reports expressions have no clock; "
                "BUILD_TIME, the time the report is built, stands in")
            return _call("strftime", [_name("BUILD_TIME")] + _args)
        if _path in ("datetime.datetime", "datetime.date"):
            _rv = self.time_constructor(_args, _keywords)
            if _rv is not None:
                return _rv
        if _path == "datetime.timedelta":
            _rv = self.duration(_args, _keywords)
            if _rv is not None:
                return _rv
        if _path == "decimal.Decimal":
            return _call("decimal", _args, _keywords)
        if _path and _path.startswith("math."):
            _member = _path[5:]
            if _member in SR_MATH:
                return _call(_attribute(_name("math"), _member), _args,
                    _keywords)
            if _member == "trunc":
                return _call("int", _args)
        self.note("%s() comes from an import, which s-reports has no "
            "counterpart for" % (_path or _dotted(node.func)))
        return ast.Call(func=node.func, args=_args, keywords=_keywords)

    def time_constructor(self, args, keywords):
        """Rewrite datetime(...) or date(...) as time.time(...)."""
        _order = ("year", "month", "day", "hour", "minute", "second",
            "microsecond")
        _fields = list(zip(_order, args)) \
            + [(_item.arg, _item.value) for _item in keywords]
        _rv = []
        for (_field, _value) in _fields:
            if _field == "microsecond":
                _field = "nanosecond"
                _value = ast.BinOp(left=_value, op=ast.Mult(),
                    right=ast.Constant(value=1000))
            elif _field not in _order:
                self.note("time.time() in s-reports takes no %s" % _field)
                return None
            _rv.append(ast.keyword(arg=_field, value=_value))
        return _call(_attribute(_name("time"), "time"), keywords=_rv)

    def duration(self, args, keywords):
        """Rewrite timedelta(...) as a sum of s-reports durations."""
        _order = ("days", "seconds", "microseconds", "milliseconds",
            "minutes", "hours", "weeks")
        _units = {
            "weeks": ("hour", 168),
            "days": ("hour", 24),
            "hours": ("hour", 1),
            "minutes": ("minute", 1),
            "seconds": ("second", 1),
            "milliseconds": ("millisecond", 1),
            "microseconds": ("microsecond", 1),
        }
        _terms = []
        for (_field, _value) in list(zip(_order, args)) \
            + [(_item.arg, _item.value) for _item in keywords]:
            if _field not in _units:
                return None
            (_unit, _factor) = _units[_field]
            _term = _attribute(_name("time"), _unit)
            if _factor != 1:
                _term = ast.BinOp(left=ast.Constant(value=_factor),
                    op=ast.Mult(), right=_term)
            _terms.append(ast.BinOp(left=_value, op=ast.Mult(), right=_term))
        if not _terms:
            return None
        _rv = _terms[0]
        for _term in _terms[1:]:
            _rv = ast.BinOp(left=_rv, op=ast.Add(), right=_term)
        return _rv

def engine_format(spec):
    """Return a % format as s-reports's format builtin takes it.

    Return value: a pair (format, notes).  The format is None
    if the specification cannot be converted.

    """
    _notes = []
    _parts = []
    _position = 0
    for _match in CONVERSION.finditer(spec):
        _parts.append(spec[_position:_match.start()])
        _position = _match.end()
        _verb = _match.group("verb")
        if _match.group("key") is not None:
            _notes.append("a %(name) conversion has no counterpart "
                "in s-reports's format")
            return (None, _notes)
        if (_match.group("width") == "*") \
        or (_match.group("precision") == "*"):
            _notes.append("a * width or precision has no counterpart "
                "in s-reports")
            return (None, _notes)
        if _verb in ("r", "a"):
            _notes.append("%%%s became %%q, which quotes strings with "
                "double quotes" % _verb)
        _verb = _VERB_SPELLINGS.get(_verb, _verb)
        if _verb not in _ENGINE_VERBS:
            _notes.append("the %%%s conversion has no counterpart in s-reports"
                % _verb)
            return (None, _notes)
        _precision = _match.group("precision")
        _parts.append("%" + _match.group("flags") + (_match.group("width")
            or "") + ("" if _precision is None else "." + _precision) + _verb)
    _parts.append(spec[_position:])
    return ("".join(_parts), _notes)

def printf_spec(spec, conversion=None):
    """Return a str.format specification as a % conversion.

    Parameters:
        spec: the format specification, as in "{:>10.2f}".
        conversion: "s", "r", "a", or None, as in "{!r}".

    Return value: a pair (conversion, notes).  The conversion
    is None if the specification has no % counterpart.

    """
    _notes = []
    _match = _FORMAT_SPEC.match(spec)
    if _match is None:
        return (None, _notes)
    _fill = _match.group("fill")
    _align = _match.group("align")
    _kind = _match.group("kind")
    _width = _match.group("width") or ""
    _precision = _match.group("precision")
    if _match.group("z") or _match.group("group"):
        return (None, _notes)
    if conversion in ("r", "a"):
        _notes.append("!%s became %%q, which quotes strings with "
            "double quotes" % conversion)
        if _kind not in (None, "s"):
            return (None, _notes)
        _kind = "q"
    elif conversion == "s":
        if _kind not in (None, "s"):
            return (None, _notes)
        _kind = "s"
    _flags = ""
    if _align == "<":
        if _fill not in (None, " "):
            return (None, _notes)
        _flags += "-"
    elif _align == "=":
        if _fill != "0":
            return (None, _notes)
        _flags += "0"
    elif _align == "^":
        return (None, _notes)
    elif _align == ">":
        if _fill not in (None, " "):
            return (None, _notes)
    elif _width and (_kind in (None, "s", "q")):
        # Python aligns text left and numbers right by default,
        # and % aligns everything right.  Without a type,
        # which of the two the value is cannot be known here.
        if _kind is None:
            return (None, _notes)
        _flags += "-"
    if _match.group("sign") in ("+", " "):
        _flags += _match.group("sign")
    if _match.group("alt"):
        _flags += "#"
    if _match.group("zero"):
        _flags += "0"
    if _kind is None:
        if _precision is not None:
            return (None, _notes)
        _kind = "s"
    elif _kind in ("n", "%"):
        return (None, _notes)
    elif _kind == "F":
        _kind = "f"
    return ("%" + _flags + _width
        + ("" if _precision is None else "." + _precision) + _kind, _notes)

# -- writing Starlark -------------------------------------------------------

def starlark_string(text):
    """Return a Starlark string literal holding the text."""
    _out = ["'"]
    for _char in text:
        _code = ord(_char)
        if _char == "\\":
            _out.append("\\\\")
        elif _char == "'":
            _out.append("\\'")
        elif _char == "\n":
            _out.append("\\n")
        elif _char == "\r":
            _out.append("\\r")
        elif _char == "\t":
            _out.append("\\t")
        elif (_code < 0x20) or (_code == 0x7f):
            _out.append("\\x%02x" % _code)
        elif 0xd800 <= _code <= 0xdfff:
            # A lone surrogate is no character; Starlark refuses one.
            _out.append("\\ufffd")
        elif (_code >= 0x80) and not _char.isprintable():
            if _code > 0xffff:
                _out.append("\\U%08x" % _code)
            else:
                _out.append("\\u%04x" % _code)
        else:
            _out.append(_char)
    _out.append("'")
    return "".join(_out)

def _starlark_bytes(data):
    """Return a Starlark bytes literal holding the data."""
    _out = ["b'"]
    for _code in data:
        _char = chr(_code)
        if _char in ("\\", "'"):
            _out.append("\\" + _char)
        elif 0x20 <= _code < 0x7f:
            _out.append(_char)
        else:
            _out.append("\\x%02x" % _code)
    _out.append("'")
    return "".join(_out)

def starlark(node):
    """Return the Starlark text of an expression tree."""
    return _emit(node, 0)

def _emit(node, minimum):
    """Return the text of a node, parenthesized below a precedence."""
    (_text, _precedence) = _render(node)
    if _precedence < minimum:
        return "(%s)" % _text
    return _text

def _render(node):
    """Return the text of a node and the precedence of its operator."""
    _handler = _RENDERERS.get(type(node))
    if _handler is None:
        # Nothing Starlark can say; write it as Python has it.
        return (ast.unparse(node), 0)
    return _handler(node)

def _render_constant(node):
    """Return the text of a constant."""
    _value = node.value
    if isinstance(_value, bool) or (_value is None):
        return (str(_value), ATOM)
    if isinstance(_value, str):
        return (starlark_string(_value), ATOM)
    if isinstance(_value, bytes):
        return (_starlark_bytes(_value), ATOM)
    if isinstance(_value, int):
        return (str(_value), ATOM)
    if isinstance(_value, float):
        _text = repr(_value)
        if _text in ("inf", "nan"):
            return ("float('%s')" % _text, PRIMARY)
        return (_text, ATOM)
    return (ast.unparse(node), 0)

def _render_attribute(node):
    """Return the text of an attribute reference."""
    _base = _emit(node.value, PRIMARY)
    if isinstance(node.value, ast.Constant) \
    and isinstance(node.value.value, (int, float)):
        _base = "(%s)" % _base
    return ("%s.%s" % (_base, node.attr), PRIMARY)

def _render_slice(node):
    """Return the text inside the brackets of a subscript."""
    if isinstance(node, ast.Slice):
        _rv = "%s:%s" % (
            "" if node.lower is None else _emit(node.lower, LAMBDA),
            "" if node.upper is None else _emit(node.upper, LAMBDA))
        if node.step is not None:
            _rv += ":" + _emit(node.step, LAMBDA)
        return _rv
    if isinstance(node, ast.Tuple):
        return ", ".join(_render_slice(_item) for _item in node.elts)
    return _emit(node, LAMBDA)

def _render_subscript(node):
    """Return the text of a subscript."""
    return ("%s[%s]" % (_emit(node.value, PRIMARY), _render_slice(node.slice)),
        PRIMARY)

def _render_argument(node):
    """Return the text of a call argument or a sequence item."""
    if isinstance(node, ast.Starred):
        return "*" + _emit(node.value, PRIMARY)
    return _emit(node, LAMBDA)

def _render_call(node):
    """Return the text of a call."""
    _args = [_render_argument(_arg) for _arg in node.args]
    for _keyword in node.keywords:
        if _keyword.arg is None:
            _args.append("**" + _emit(_keyword.value, PRIMARY))
        else:
            _args.append("%s=%s" % (_keyword.arg,
                _emit(_keyword.value, LAMBDA)))
    return ("%s(%s)" % (_emit(node.func, PRIMARY), ", ".join(_args)),
        PRIMARY)

def _render_binop(node):
    """Return the text of a binary operation."""
    (_op, _precedence) = _BINARY[type(node.op)]
    return ("%s %s %s" % (_emit(node.left, _precedence), _op,
        _emit(node.right, _precedence + 1)), _precedence)

def _render_unaryop(node):
    """Return the text of a unary operation."""
    if isinstance(node.op, ast.Not):
        return ("not " + _emit(node.operand, NOT), NOT)
    _op = _UNARY[type(node.op)]
    _operand = _emit(node.operand, UNARY)
    if _operand[:1] in ("+", "-", "~"):
        _operand = " " + _operand
    return (_op + _operand, UNARY)

def _render_boolop(node):
    """Return the text of and or or."""
    if isinstance(node.op, ast.And):
        (_op, _precedence) = ("and", AND)
    else:
        (_op, _precedence) = ("or", OR)
    return ((" %s " % _op).join(_emit(_item, _precedence + 1)
        for _item in node.values), _precedence)

def _render_compare(node):
    """Return the text of a comparison."""
    _parts = [_emit(node.left, COMPARE + 1)]
    for (_op, _right) in zip(node.ops, node.comparators):
        _parts.append(_COMPARE[type(_op)])
        _parts.append(_emit(_right, COMPARE + 1))
    return (" ".join(_parts), COMPARE)

def _render_ifexp(node):
    """Return the text of a conditional expression."""
    return ("%s if %s else %s" % (_emit(node.body, IFEXP + 1),
        _emit(node.test, IFEXP + 1), _emit(node.orelse, IFEXP)), IFEXP)

def _render_lambda(node):
    """Return the text of a lambda."""
    _args = ", ".join(_arg.arg for _arg in node.args.args)
    return ("lambda %s: %s" % (_args, _emit(node.body, LAMBDA)), LAMBDA)

def _render_sequence(items):
    """Return the text of the items of a tuple or a list."""
    return ", ".join(_render_argument(_item) for _item in items)

def _render_tuple(node):
    """Return the text of a tuple."""
    _text = _render_sequence(node.elts)
    if len(node.elts) == 1:
        _text += ","
    return ("(%s)" % _text, ATOM)

def _render_list(node):
    """Return the text of a list."""
    return ("[%s]" % _render_sequence(node.elts), ATOM)

def _render_dict(node):
    """Return the text of a dict."""
    _items = []
    for (_key, _value) in zip(node.keys, node.values):
        if _key is None:
            _items.append("**" + _emit(_value, PRIMARY))
        else:
            _items.append("%s: %s" % (_emit(_key, LAMBDA),
                _emit(_value, LAMBDA)))
    return ("{%s}" % ", ".join(_items), ATOM)

def _render_target(node):
    """Return the text of a comprehension target."""
    if isinstance(node, ast.Tuple):
        return ", ".join(_render_target(_item) for _item in node.elts)
    return _emit(node, PRIMARY)

def _render_generators(generators):
    """Return the text of the for and if clauses of a comprehension."""
    _parts = []
    for _generator in generators:
        _parts.append(" for %s in %s" % (_render_target(_generator.target),
            _emit(_generator.iter, OR)))
        for _condition in _generator.ifs:
            _parts.append(" if " + _emit(_condition, OR))
    return "".join(_parts)

def _render_listcomp(node):
    """Return the text of a list comprehension."""
    return ("[%s%s]" % (_emit(node.elt, LAMBDA),
        _render_generators(node.generators)), ATOM)

def _render_dictcomp(node):
    """Return the text of a dict comprehension."""
    return ("{%s: %s%s}" % (_emit(node.key, LAMBDA),
        _emit(node.value, LAMBDA), _render_generators(node.generators)),
        ATOM)

_RENDERERS = {
    ast.Constant: _render_constant,
    ast.Name: lambda node: (node.id, ATOM),
    ast.Attribute: _render_attribute,
    ast.Subscript: _render_subscript,
    ast.Call: _render_call,
    ast.BinOp: _render_binop,
    ast.UnaryOp: _render_unaryop,
    ast.BoolOp: _render_boolop,
    ast.Compare: _render_compare,
    ast.IfExp: _render_ifexp,
    ast.Lambda: _render_lambda,
    ast.Tuple: _render_tuple,
    ast.List: _render_list,
    ast.Dict: _render_dict,
    ast.ListComp: _render_listcomp,
    ast.DictComp: _render_dictcomp,
}

# vim: set et sts=4 sw=4 :
