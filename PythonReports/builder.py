"""PythonReports builder"""
# FIXME: column-based variables are not intelligible

__all__ = ["Builder"]

import itertools
import math
import os
import sys
import time
import threading
from warnings import warn

from PythonReports import barcode, drivers
from PythonReports import template as prt
from PythonReports import printout as prp
from PythonReports import segment_layout
from PythonReports.datatypes import *


class ExpressionError(RuntimeError):

    """A wrapper for errors raised by expression evaluation

    @ivar error: the original exception

    @ivar expr: the expression string

    @ivar template: template element containing the expression

    """

    def __init__(self, error, expr, template=None):
        self.error = error
        self.expr = expr
        self.template = template

    def __unicode__(self):
        if self.template is None:
            _where = None
        elif isinstance(self.template, Element):
            _where = element_label(self.template)
        else:
            _where = repr(self.template)
        if _where:
            _rv = "%s evaluating %r in %s" % (self.error, self.expr, _where)
        else:
            _rv = "%s evaluating %r" % (self.error, self.expr)
        return _rv

    def __str__(self):
        return unicode(self).encode("utf-8")

class Variable(object):

    """Report variable

    Variables accumulate data values while report data sequence
    is iterated.  The value property performs the calculation
    on the accumulated sequence.

    """

    # attributes initialized from template element
    name = REQUIRED
    expr = REQUIRED
    init = None
    calc = "first"
    iter = "detail"
    itergrp = None
    reset = "report"
    resetgrp = None
    template = None

    # Most variables use builtin list to accumulate values
    # these helper classes are used in special cases
    # for uniform accumulation calls

    class _Accumulator(object):
        """Base class for value accumulators"""
        # pylint: disable-msg=R0903
        # R0903: Too few public methods
        def append(self, value):
            """Add a value to the accumulated sequence"""

    class AccumulateFloat(_Accumulator, list):
        """Accumulator forcing all values to be float"""
        def append(self, value):
            """Add a value to the accumulated sequence"""
            super(Variable.AccumulateFloat, self).append(float(value))

    ### calculation types

    @staticmethod
    def first(value):
        """Return the first element of the value sequence"""
        return value[0] if value else None

    @staticmethod
    def last(value):
        """Return the last element of the value sequence"""
        return value[-1] if value else None

    @staticmethod
    def chain(value):
        """Return elements of the value sequence joined into single list

        The elements are assumed to be sequences.

        """
        _rv = []
        for _item in value:
            try:
                _sequence = iter(_item)
            except:
                _rv.append(_item)
            else:
                _rv.extend(_sequence)
        return _rv

    @staticmethod
    def set(value):
        """Return a set of the elements in the value sequence"""
        return set(value)

    @staticmethod
    def count(value):
        """Return number of different elements in the value sequence"""
        return len(frozenset(value))

    @staticmethod
    def avg(value):
        """Return an average value of a float sequence"""
        return sum(value) / len(value)

    @staticmethod
    def min(value):
        """Return minimal value of the value sequence"""
        return min(value)

    @staticmethod
    def max(value):
        """Return maximal value of the value sequence"""
        return max(value)

    @staticmethod
    def var(value):
        """Return variance from the average of a float sequence"""
        _avg = Variable.avg(value)
        return sum([(_item - _avg) ** 2 for _item in value]) / len(value)

    @staticmethod
    def std(value):
        """Return standard deviation of a float sequence"""
        return math.sqrt(Variable.var(value))

    # sum must be defined last to use builtin sum in other calculations
    @staticmethod
    def sum(value):
        """Return sum of the sequence values

        If values are strings, return concatenated string.

        """
        if isinstance(value[0], basestring):
            return "".join(value)
        else:
            return sum(value)

    def __init__(self, template):
        """Create report variable

        Parameters:
            template: instance of template.Variable

        """
        super(Variable, self).__init__()
        self.template = template
        for _name in prt.Variable.attributes:
            setattr(self, _name, template.get(_name))
        # FIXME? accumulator class and computing function for
        #   calculation variants may be defined at class level
        #   (faster because won't use object attribute lookup)
        (self._accumulator, self._compute) = {
            None: (list, self.last),
            "first": (list, self.first),
            "last": (list, self.last),
            "count": (list, self.count),
            "list": (list, None),
            "set": (list, self.set),
            "chain": (list, self.chain),
            "sum": (list, self.sum),
            "avg": (self.AccumulateFloat, self.avg),
            "min": (list, self.min),
            "max": (list, self.max),
            "std": (self.AccumulateFloat, self.std),
            "var": (self.AccumulateFloat, self.var),
        }[self.calc]
        # values must be initialized with start()
        # this is a dummy to make pylint/pychecker happy
        self.values = []

    def start(self, context):
        """Reset the variable (start value accumulation)

        Parameters:
            context: expression evaluation context,
                used to compute initial value

        """
        if self.init:
            _init = [context.eval(self.init, self.template)]
        else:
            _init = []
        self.values = self._accumulator(_init)

    def iterate(self, context):
        """Store next value of the iteration sequence

        Parameters:
            context: expression evaluation context

        """
        self.values.append(context.eval(self.expr, self.template))

    def rollback(self):
        """Undo last iteration"""
        if self.init:
            _fence = 1
        else:
            _fence = 0
        if len(self.values) > _fence:
            del self.values[-1]

    @property
    def value(self):
        """Variable evaluation result"""
        if not self.values:
            if self.calc in ("list", "chain"):
                return []
            elif self.calc == "set":
                return set()
            else:
                return None
        elif self._compute:
            return self._compute(self.values)
        else:
            return self.values

    def __repr__(self):
        return "<%s@%X \"%s\" %r>" % (self.__class__.__name__, id(self),
            self.name, self.values)


class Context(object):

    """Expression evaluation context"""

    # name lookup is performed in order of this list
    __slots__ = ["sysvars", "imports", "parameters", "variables"]

    # names of the predefined variables
    # (additional *_COUNT variables may be created for report groups)
    PREDEFINED_VARIABLES = (
        "THIS", "ITEM_NUMBER",
        "DATA_COUNT", "REPORT_COUNT", "PAGE_COUNT", "COLUMN_COUNT",
        "PAGE_NUMBER", "COLUMN_NUMBER",
        "VERTICAL_POSITION", "VERTICAL_SPACE",
    )

    def __init__(self, *args, **kwargs):
        _attrs = dict([(_name, {}) for _name in self.__slots__])
        _attrs.update(kwargs)
        if args:
            _attrs.update(zip(self.__slots__, args))
        # each context has it's own dictionary of predefined
        # variables, all other collections may be shared
        # between different contexts.
        # all predefined variables must be present.
        self.sysvars = dict.fromkeys(self.PREDEFINED_VARIABLES, 0)
        self.sysvars.update(_attrs.pop("sysvars", {}))
        # copy remaining collections
        for (_name, _value) in _attrs.iteritems():
            setattr(self, _name, _value)

    def __repr__(self):
        return "<%s.%s object:\n%s\n-- at %x>" % (
            self.__class__.__module__, self.__class__.__name__,
            "\n".join(("%s: %r" % (_name, getattr(self, _name))
                for _name in self.__slots__)),
            id(self)
        )

    # mapping/evaluation interface

    def __getitem__(self, name):
        for _cname in self.__slots__:
            _collection = getattr(self, _cname)
            try:
                _value = _collection[name]
            except KeyError:
                continue
            if _cname == "variables":
                _value = _value.value
            return _value
        _data = self.sysvars["THIS"]
        try:
            return _data[name]
        except (TypeError, KeyError):
            try:
                return getattr(_data, name)
            except AttributeError:
                raise KeyError, name

    def __setitem__(self, name, value):
        self.sysvars[name] = value

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

    def eval(self, expression, template=None):
        """Evaluate expression in this context

        @param expression: Python expression to evaluate.


        @param template: template element containing the expression.

            Used in error reporting.

        @return: expression evaluation result.

        """
        __slots__ = ["sysvars", "imports", "parameters", "variables"]
        # Generator expressions run in their own local context,
        # name defined in the locals dictionary are not visible there.
        # Make globals dictionary from all known names.
        _globals = {}
        for _name in reversed(self.__slots__):
            _globals.update(getattr(self, _name))
        try:
            return eval(expression, _globals, self)
        except Exception, _err:
            raise ExpressionError(_err, expression, template), \
                None, sys.exc_info()[2]

    # utilities

    def copy(self):
        """Return new context with identical contents"""
        return self.__class__(**dict([(_name, getattr(self, _name))
            for _name in self.__slots__]))

    def add_variables(self, *variables):
        """Add report variable definitions

        Arguments are instances of the Variable class.

        """
        for _var in variables:
            self.variables[_var.name] = _var

    def load_imports(self, report):
        """Process import declarations in given report ElementTree"""
        for _item in report.findall("import"):
            # cast 'path' to str cause of __import__(fromlist) doesn't
            # support unicode
            _path = str(_item.get("path")).rsplit(".", 1)
            if len(_path) > 1:
                _module = __import__(_path[0], fromlist=[_path[1]])
                _module = getattr(_module, _path[1])
            else:
                # support for single component paths
                _module = __import__(_path[0])

            self.imports[_item.get("alias") or _path[-1]] = _module

class ReportElement(Structure):

    """Printable report element

    This is a simple structure keeping references
    to template element and containing output section,
    an output style for the element and bounding box
    position and size.

    May also hold any additional info needed for the builder.

    For now (this may change in the future) ReportElement does no
    processing by itself; all the brains are in the Section objects.

    """

    # pylint: disable-msg=R0903
    # R0903: Too few public methods

    ### attributes:
    #
    # section: containing section object
    # template: template element
    # style: dictionary of style attributes
    # printable: False if the element is suppressed (by style printwhen)
    # tbox: box defined in the template
    # bbox: box with absolute sizes (computed from tbox and section sizes)
    # obox: output box, with absolute position and size values

    # additional attributes for "field" elements:
    #
    # text: text value acquired from data or expression evaluation
    # otext: output text, wrapped to box width

    # make pylint happy
    section = template = style = printable = None
    tbox = bbox = obox = text = otext = None

    def __repr__(self):
        for _box in (self.obox, self.bbox, self.tbox):
            if _box is not None:
                break
        if (_box is None) or (self.template is None):
            _rv = "<%s@%X>" % (
                self.__class__.__name__, id(self))
        else:
            _rv = "<%s@%X(%.1f, %.1f, %.1f, %.1f): %s>" % (
                self.__class__.__name__, id(self),
                _box.x, _box.y, _box.width, _box.height, self.template.tag)
        return _rv

class Section(list):

    """Output section

    Objects of this class fill a sections of the report,
    i.e. title, summary, header, footer and detail sections.

    After a section is built it acts like a list of ReportElement objects.

    """

    # Printout classes and attributes to copy from templates
    PRINTOUTS = dict(
        (_prt.tag, (_prp, set(_prt.attributes) & set(_prp.attributes)))
        for (_prt, _prp) in (
            (prt.Field, prp.Text),
            (prt.Line, prp.Line),
            (prt.Rectangle, prp.Rectangle),
            (prt.Image, prp.Image),
            (prt.BarCode, prp.BarCode),
            (prt.Outline, prp.Outline),
        ))

    # Bar Code drivers
    BARCODES = {
        "Code128": barcode.code128,
        "Code39": barcode.code39,
        "2of5i": barcode.code2of5i,
        "Aztec": barcode.aztec,
        "QR-L": barcode.qr_l,
        "QR-M": barcode.qr_m,
        "QR-Q": barcode.qr_q,
        "QR-H": barcode.qr_h,
    }

    # Tag names for printable output elements (with dimension boxes)
    PRINTABLE_ELEMENT_TAGS = frozenset(("field",
        "line", "rectangle", "image", "barcode"))

    # printability is set by .build
    printable = None

    # map template items to self's elements
    # for floating segment layout calculation
    template2element = None

    # TODO create specific class for template's section elements

    # mark whether the section has floating boxes or not
    has_floating_boxes = False

    # the vertical layout of floating boxes is 1D problem, so
    # boxes become segments.  Each segment has
    # C{(template y, template height, floating mark,
    #   segment number for debug,
    #   template item that produced the segment)}
    # The last segment's item is used as index in C{template2element}
    # for calculating actual segment height.
    vertical_segment_layout = None

    def __init__(self, builder, template, context=None):
        """Create Section instance

        Parameters:
            builder: report builder object
                used to register deferred evaluations
                and to get named fonts and datablocks
            template: section template
            context: optional section context
                if passed, the section will be automatically built
                for this context

        """
        super(Section, self).__init__()
        self.builder = builder
        self.template = template
        self.box = self.tbox = Box.from_element(template.find("box"))
        self.resizeable = False
        # subreports and bookmarks lists are created in .build()
        self.subreports_before = self.subreports_after = self.bookmarks = ()
        self.template2element = {}
        self.vertical_segment_layout = self.has_floating_boxes = None
        self.create_vertical_segment_layout(template)
        if context:
            self.build(context)

    def create_vertical_segment_layout(self, template):
        """Set C{template}'s C{vertical_segment_layout} if missing.

        Also sets C{has_floating_boxes}.

        """
        _elements = [(_item, Box.from_element(_item.find("box")))
            for _item in template
            if _item.tag in self.PRINTABLE_ELEMENT_TAGS]

        self.has_floating_boxes = any(_it[1].float and
            (_it[1].y >= 0) and (_it[1].height >= 0) for _it in _elements)
        if not self.has_floating_boxes:
            template.vertical_segment_layout = (lambda *args: None)
            return

        # non-floating segments should precede floating ones
        _segments = [(_box.y, _box.height, _box.float, _nn, _item)
            for (_nn, (_item, _box)) in enumerate(_elements)
            if (_box.y >= 0) and (_box.height >= 0)]

        _graph = self.arrange_segments(_segments)

        #template.vertical_segment_layout
        self.vertical_segment_layout = \
            segment_layout.SegmentLayout(dict(_graph))

    @staticmethod
    def arrange_segments(segments):
        """@return: minimal DAG of floating segment dependencies.

        @param segments: tuple, where first 3 items are C{(y, height,
            floating)}, where C{floating} is boolean flag that the segment
            should float depending on segments wholly above the segment.

        Segments precede other when it is wholly above it concerning
        - a static segment precede a floating segment, because third
          segment's item is boolean;
        - a floating segment precede other floating segment only when
          it starts earlier for the case when the second floating segment
          has zero height.

        Dependency is transitive.  Minimal dependency is one that does not
        contain items that are implied by other dependency items.  Examle:
        when B depends on A and C depends on A and B, minimal dependency for C
        will contain B only.

        About segments minimal dependency should be much smaller than full one.

        >>> arrange = Section.arrange_segments
        >>> arrange([])
        []

        >>> arrange([(0, 1, False)])
        [((0, 1, False), [])]

        >>> arrange([(0, 1, True), (2, 1, False)])
        [((0, 1, True), []), ((2, 1, False), [])]

        >>> arrange([(0, 1, True), (2, 1, True)])
        [((0, 1, True), []), ((2, 1, True), [(0, 1, True)])]

        >>> val = arrange([(0, 1, False), (2, 1, True), (4, 1, True)])
        >>> print "\\n".join(repr(it) for it in val)
        ((0, 1, False), [])
        ((2, 1, True), [(0, 1, False)])
        ((4, 1, True), [(2, 1, True)])

        >>> val = arrange([(0, 0, False, 1), (0, 0, False, 2),
        ...   (0, 0, True, 3), (0, 0, True, 4), (10, 0, True, 5),
        ...   (5, 20, True, 6)])
        >>> print "\\n".join(repr((s, sorted(p))) for (s, p) in sorted(val))
        ((0, 0, False, 1), [])
        ((0, 0, False, 2), [])
        ((0, 0, True, 3), [(0, 0, False, 1), (0, 0, False, 2)])
        ((0, 0, True, 4), [(0, 0, False, 1), (0, 0, False, 2)])
        ((5, 20, True, 6), [(0, 0, True, 3), (0, 0, True, 4)])
        ((10, 0, True, 5), [(0, 0, True, 3), (0, 0, True, 4)])

        """
        _rv = dict((_seg, []) for _seg in segments)
        for (_seg, _pre) in segment_layout.preceding_segments(segments):
            if _seg[2]:
                # floating segments with the same starting point
                # has *no* influence to the current segment
                _pre = [_sp for _sp in _pre
                    if not _sp[2] or (_sp[0] < _seg[0])]
                # remove extra dependencies,
                # i.e. dependencies of preceding floating segments
                _remove = itertools.chain(*(
                    _rv[_sp] for _sp in _pre if _sp[2]))
                _pre = list(set(_pre) - set(_remove))
            else:
                _pre = []
            _rv[_seg] = _pre
        return _rv.items()

    def iter_styles(self):
        """Iterate over all styles for the section (both direct and inherited)
        """
        _element = self.template
        _parents = self.builder.layout_parents
        # all sections except detail (i.e. header, footer, title and summary)
        # extend over all columns defined in their immediate parent.
        # therefore parent columns styles must be ignored.
        if _element.tag == "detail":
            _skip_columns = 1
        else:
            _skip_columns = 2 # self and parent
        while _element is not None:
            if _skip_columns:
                _skip_columns -= 1
            else:
                for _style in _element.findall("columns/style"):
                    yield _style
            for _style in _element.findall("style"):
                yield _style
            _element = _parents[_element]

    def check_printable(self, context):
        """Return True if the section is printable in given context

        Return value is cached and may be obtained later from the
        .printable attribute.  (This allows to avoid repeated
        evaluation when .build() is called.)

        """
        def _ifirst(seq, N=1):
            return list(itertools.islice(seq, N))
        _printwhen = _ifirst(_style.get("printwhen")
            for _style in self.iter_styles()
            if context.eval(_style.get("when"), self.template)
                and _style.get("printwhen"))
        self.printable = (not _printwhen) \
            or context.eval(_printwhen[0], self.template)
        return bool(self.printable)

    def compose_style(self, context, need_attrs, styles):
        """Return style attributes collected from a style sequence

        Parameters:
            context: expression evaluation context
            need_attrs: names of the style attributes to collect
                processing stops when all these attributes
                are set to non-empty value or when the sequence
                is exhausted
            styles: sequence of dictionary-like objects

        Return value: dictionary containing all names from need_attrs.
        If some of the attributes are not filled, their values will be None.

        """
        _attrs = {}
        _count = len(need_attrs)
        for _style in styles:
            _when = _style.get("when", None)
            if (_when is None) or context.eval(_when, self.template):
                for _name in need_attrs:
                    if _name in _attrs:
                        continue
                    _attr = _style.get(_name, None)
                    if _attr is not None:
                        _attrs[_name] = _attr
                # stop when all need_attrs are collected
                if len(_attrs) == _count:
                    break
        else:
            # the loop didn't break, some attributes are not filled
            for _name in need_attrs:
                _attrs.setdefault(_name, None)
        return _attrs

    def set_text_value(self, context, element):
        """Attach initial text value to field or barcode element.

        Parameters:
            context: expression evaluation context
            element: ReportElement object with Field or BarCode template

        The "text" attribute of the element object will be set
        by the first applicable of the following rules:

            - if expr is unset, use data block
            - if evaltime is not empty and data block found, use data block
            - evaluate expr and use it's result

        """
        _template = element.template
        _data = _template.get("data") # name of data block defined at top level
        if _data:
            _data = self.builder.template.datablocks[_data]
        else:
            _data = _template.find("data")
        _expr = _template.get("expr")
        if _expr:
            if _template.get("evaltime") and (_data is not None):
                _value = prt.Data.get_data(_data, context)
            else:
                _value = context.eval(_expr, self.template)
        elif _data is not None:
            _value = prt.Data.get_data(_data, context)
        else:
            _value = None
        if _value is None:
            element.text = u""
        else:
            element.text = _template.get("format", "%s") % _value

    def build(self, context):
        """Create section contents

        Parameters:
            context: expression evaluation context

        Fill the list with ReportElement instances for all
        template elements.

        """
        self.check_printable(context)
        # reset
        self[:] = []
        # if the section is suppressed do nothing
        if not self.printable:
            return
        _elements = getchildren(self.template)
        # section is resizeable if it's height is not fixed
        # then final size must be recalculated after filling
        self.resizeable = self.tbox.height <= 0
        if not self.resizeable:
            # look for stretchable texts
            # or barcodes (always stretchable)
            # or growable images.
            for _item in _elements:
                _tag = _item.tag
                if (((_tag == "field") and _item.get("stretch"))
                    or (_tag == "barcode")
                    or ((_tag == "image") and (_item.get("scale") == "grow"))
                ):
                    self.resizeable = True
                    break
        _default_element_style = [self.compose_style(context,
            ("font", "color", "bgcolor"), self.iter_styles())]
        _subreports = []
        _bookmarks = []
        for _item in _elements:
            if _item.tag == "subreport":
                _when = _item.get("when")
                if (not _when) or context.eval(_when, _item):
                    _subreports.append((_item.get("seq"), _item))
                continue
            if _item.tag == "outline":
                _bookmarks.append(Structure(template=_item,
                    name=self.builder.generate_id(),
                    title=context.eval(_item.get("title"), _item)))
                continue
            if _item.tag not in self.PRINTABLE_ELEMENT_TAGS:
                continue
            _element = ReportElement(section=self, template=_item)
            self.template2element[_item] = _element
            _element.style = self.compose_style(context,
                ("printwhen", "font", "color", "bgcolor"),
                _item.findall("style") + _default_element_style)
            _printwhen = _element.style.get("printwhen")
            _element.printable = not _printwhen \
                or context.eval(_printwhen, _item)
            # must not evaluate expressions for suspended elements.
            # skip elements that are not printable.
            if not _element.printable:
                continue
            _element.tbox = Box.from_element(_item.find("box"))
            if _item.tag in ("field", "barcode"):
                self.set_text_value(context, _element)
                if _item.get("evaltime"):
                    self.builder.register_eval(_element)
                if _item.tag == "barcode":
                    _element.barcode_text = None
            elif _item.tag == "image":
                _element.image = self.builder.image(_item)
                # FIXME: use_count should be incremented in Builder.image()
                _element.image.use_count += 1
            self.append(_element)
        _subreports.sort()
        self.subreports_before = tuple(_item[1] for _item in _subreports
            if _item[0] < 0)
        self.subreports_after = tuple(_item[1] for _item in _subreports
            if _item[0] > 0)
        self.bookmarks = tuple(_bookmarks)

    def build_barcode(self, element):
        """Compute sripe widths and box size/position for barcode element

        If the text attribute is changed since previous call,
        recalculate the symbol and update element's bounding box.

        """
        if element.text == element.barcode_text:
            # the text was not changed since previous call
            return
        _xdim = element.template.get("module")
        _code = self.BARCODES[element.template.get("type")]
        _stripes = _code(element.text)
        element.stripes = _code.add_qz(_stripes, _xdim)
        # The module may be adjusted for growing 2D codes
        element.module = _xdim
        element.is_2d = _code.IS_2D
        if not element.is_2d:
            # 1D codes produce one tuple. Make it 2-dimensional for simplicity.
            element.stripes = (element.stripes,)
        # expand the bounding box if needed
        _min_height = _code.min_height(_stripes, _xdim)
        # Assume all rows have the same width
        _min_width = math.ceil(sum(element.stripes[0]) * _xdim / 1000. * 72)
        if element.template.get("vertical"):
            (_min_height, _min_width) = (_min_width, _min_height)
        _bbox = element.tbox.copy()
        # Always apply minimums here, actual sizes calculated in .refill()
        _bbox.width = _min_width
        _bbox.height = _min_height
        _bbox.place_x(self.box)
        _bbox.place_y(self.box)
        element.bbox = _bbox
        # remember the text of the symbol -
        # will skip build unless the text is changed
        element.barcode_text = element.text

    def fill(self, x, y, width, bottom):
        """Compute section layout within given dimensions

        Parameters:
            x, y: position of the left upper corner
            width: width of the available space
            bottom: y position of the bottom of available space

        """
        _text_drivers = self.builder.text_drivers
        # create section placement box
        _sbox = self.box = self.tbox.copy()
        _bbox = Box(x, y, width, bottom - y)
        _sbox.place_x(_bbox)
        _sbox.place_y(_bbox)
        # Note: vertical alignment is ignored for section boxes
        _sbox.align_x(_bbox)
        # fix widths, wrap texts, estimate heights
        for _element in self:
            _bbox = _element.tbox.copy()
            _bbox.place_x(_sbox)
            _template = _element.template
            # for the purposes of the section height estimation
            # we cannot use boxes with height offset from the section bottom
            # because we don't know yet where the bottom is.
            # still, we can estimate height for stretchable boxes.
            if _template.tag == "field":
                _stretch = _template.get("stretch")
                if _stretch or (_bbox.height >= 0):
                    _driver = _text_drivers[_element.style["font"]]
                    if _stretch:
                        # expand box height to suffice for the whole text
                        _otext = _driver.wrap(_element.text, _bbox.width)
                    else:
                        # make sure the box is high enough for one row of text
                        _otext = _element.text.split("\n")[0]
                    _height = _driver.getsize(_otext)[1]
                    if _bbox.height < _height:
                        _bbox.height = _height
            elif (_template.tag == "image"):
                (_width, _height) = _element.image.getsize()
                if _template.get("scale") == "grow":
                    # make sure the box is big enough for the picture
                    if 0 <= _bbox.width < _width:
                        _bbox.width = _width
                    if 0 <= _bbox.height < _height:
                        _bbox.height = _height
                else:
                    # adjust "autosize" dimensions, if any
                    if _bbox.width == 0:
                        _bbox.width = _width
                    if _bbox.height == 0:
                        _bbox.height = _height
            elif _template.tag == "barcode":
                self.build_barcode(_element)
                # bbox was built from symbol metrics
                _bbox = _element.bbox
                # undo vertical placement - section resizing requires
                # that elements are not placed vertically
                # (i.e. y coordinate for the bounding box
                # is relative to the section margin).
                _bbox.y = _element.tbox.y
            _element.bbox = _bbox

        self.move_floating_elements()

        # fix section height (may not be computed from total available height)
        if self.resizeable:
            _height = self.tbox.height
            for _element in self:
                if _element.template.tag == "barcode":
                    # For barcodes, bbox is minimum allowed.
                    # If there is bigger fixed size in the template,
                    # use that size instead of bbox minimum.
                    _bbox = _element.bbox.copy()
                    if _element.tbox.width > _bbox.width:
                        _bbox.width = _element.tbox.width
                    if _element.tbox.height > _bbox.height:
                        _bbox.height = _element.tbox.height
                else:
                    _bbox = _element.bbox
                # Note: bbox vertical dimensions are relative yet
                if (_bbox.height < 0) and (_element.template.tag == "image") \
                and (_element.template.get("scale") == "grow"):
                    # box height is relative to section size
                    # which must grow to hold the image.
                    # absolute value of _bbox.height is bottom padding.
                    _elem_height = _element.image.getsize()[1] - _bbox.height
                    if _bbox.y > 0:
                        _elem_height += _bbox.y
                elif _bbox.y < 0:
                    # the element was placed relatively to section bottom
                    # FIXME? height may be negative too
                    _elem_height = max(1 - _bbox.y, _bbox.height)
                elif _bbox.height >= 0:
                    _elem_height = _bbox.y + _bbox.height
                else:
                    # fixed space from top and bottom, unknown size
                    _elem_height = _bbox.y + 1 - _bbox.height
                if _elem_height > _height:
                    _height = _elem_height
            _sbox.height = round(_height) if _height > 0 else 0
        # fix vertical dimensions for elements
        for _element in self:
            _template = _element.template
            _bbox = _element.bbox
            _bbox.place_y(_sbox)
            if _template.tag != "image":
                continue
            # keep current bbox dimensions
            _obox = _bbox.copy()
            # shrink bounding box to image dimensions
            # Note: for "grow" images bbox should be grown yet.
            (_width, _height) = map(float, _element.image.getsize())
            if _template.get("proportional") \
            and (_template.get("scale") != "cut"):
                _ratio = min(_bbox.width / _width, _bbox.height / _height)
                _bbox.width = _width * _ratio
                _bbox.height = _height * _ratio
            else:
                # shrink dimensions independently
                if _bbox.width > _width:
                    _bbox.width = _width
                if _bbox.height > _height:
                    _bbox.height = _height
            # apply alignment
            _bbox.align_x(_obox)
            _bbox.align_y(_obox)
        # compute output boxes
        self.refill()

    def move_floating_elements(self):
        """Move floating boxes using C{vertical_segment_layout}"""
        if not self.has_floating_boxes:
            return
        def _height(segment):
            _element = self.template2element[segment[-1]]
            return _element.bbox.height if _element.printable else 0
        for (_seg, _y) in self.vertical_segment_layout(_height).iteritems():
            _element = self.template2element[_seg[-1]]
            if _element.printable:
                _element.bbox.y = _y

    def refill(self, new_y=None):
        """Update section element placements.

        Called when vertical position of the section changes
        and after deferred evaluation of field expressions.
        The size of the section is not changed.

        """
        if new_y is None:
            _sbox = None
        else:
            _sbox = self.box
            _sbox.y = new_y
        _text_drivers = self.builder.text_drivers
        for _element in self:
            if _element.template.tag == "barcode":
                # update encoded symbol and bbox from current text if needed
                self.build_barcode(_element)
                # Do the final placement: align width, grow height
                _pbox = _element.tbox.copy()
                _pbox.place_x(self.box)
                _pbox.place_y(self.box)
                _obox = _element.bbox.copy() # Minimal allowed dimensions
                if not _element.template.get("grow"):
                    # Align both dimensions.
                    _obox.align_x(_pbox)
                    _obox.align_y(_pbox)
                elif _element.is_2d:
                    # Change the module to use maximum of the box space
                    # (assume the code has equal height and width)
                    assert _obox.width == _obox.height
                    _avail = min(_pbox.width, _pbox.height)
                    if _avail > _obox.width:
                        _element.module = _avail * 1000.0 / 72 \
                            / len(_element.stripes)
                        _obox.width = _obox.height = _avail
                    _obox.align_x(_pbox)
                    _obox.align_y(_pbox)
                elif _element.template.get("vertical"):
                    # Align vertically, grow horizontally.
                    _obox.align_y(_pbox)
                    if _obox.width < _pbox.width:
                        _obox.width = _pbox.width
                else:
                    # Align horizontally, grow vertically.
                    _obox.align_x(_pbox)
                    if _obox.height < _pbox.height:
                        _obox.height = _pbox.height
                _element.obox = _obox
                # No more adjustments for barcodes.
                continue
            _bbox = _element.bbox
            if _sbox:
                # vertical position changed.  recalc from template.
                _bbox.y = _element.tbox.y
                _bbox.place_y(_sbox)
            _obox = _bbox.copy()
            if _element.template.tag == "field":
                _driver = _text_drivers[_element.style["font"]]
                _element.otext = _driver.wrap(_element.text, _bbox.width)
                (_width, _height) = _driver.getsize(_element.otext)
                if _height > _bbox.height:
                    _element.otext = _driver.chop(_element.otext, _bbox.height)
                    _obox.height = _driver.getsize(_element.otext)[1]
                else:
                    _obox.height = _height
                # don't shrink the box in horizontal dimension
                # unless required by box-based horizontal alignment.
                # (we may need full width for text alignment.)
                if _obox.halign != "left":
                    _obox.width = _width
            _obox.align_x(_bbox)
            _obox.align_y(_bbox)
            _element.obox = _obox

    def output(self, page):
        """Create printout elements on printout page

        Parameters:
            page: printout.Page object

        """
        for _element in self.bookmarks:
            _template = _element.template
            (_prp_type, _prp_attrs) = self.PRINTOUTS[_template.tag]
            _attrib = dict([(_name, _template.get(_name, ""))
                for _name in _prp_attrs])
            # 01-apr-2017 The only bookmarks type is Outline
            _attrib.update(dict(x=self.box.x, y=self.box.y,
                name=_element.name, title=_element.title,
            ))
            _prp_element = SubElement(page, _prp_type.tag, _attrib)
        for _element in self:
            # build definition for printout element
            _template = _element.template
            (_prp_type, _prp_attrs) = self.PRINTOUTS[_template.tag]
            _prp_tag = _prp_type.tag
            _attrib = dict([(_name, _template.get(_name, ""))
                for _name in _prp_attrs])
            # add style attributes (must be done before constructor is called)
            if _prp_tag == "text":
                _attrib["font"] = _element.style["font"]
                _attrib["color"] = _element.style["color"]
            elif _prp_tag == "line":
                _attrib["color"] = _element.style["color"]
            elif _prp_tag == "rectangle":
                _attrib["pencolor"] = _element.style["color"]
                if _template.get("opaque"):
                    _attrib["color"] = _element.style["bgcolor"]
            elif _prp_tag == "barcode":
                _attrib["stripes"] = " ".join(",".join(str(_stripe)
                    for _stripe in _row) for _row in _element.stripes)
                # We may have changed the module size
                _attrib["module"] = "%.2f" % _element.module
                _attrib["value"] = _element.text
            elif _prp_tag == "image":
                _image = _element.image
                if _image.name:
                    _attrib["data"] = _image.name
                elif _image.filepath and not _template.get("embed"):
                    _attrib["file"] = _image.filepath
                # override type (all images are output as jpeg or png)
                _attrib["type"] = _image.preferred_type
                # "scale" is boolean in prp: False to cut
                _attrib["scale"] = Boolean(
                    _template.get("scale") in ("fill", "grow"))
            # create printout element
            _prp_element = SubElement(page, _prp_tag, _attrib)
            _element.obox.make_element(_prp_element)
            # add content (text and images)
            if _template.tag == "field":
                # TODO: encoding, compression
                prp.Data.make_element(_prp_element, {}, _element.otext)
            elif (_template.tag == "image"):
                _image = _element.image
                if not _image.name \
                and ((not _image.filepath) or _template.get("embed")):
                    # bitmap is kept in an anonymous data block
                    prp.Data.make_element(_prp_element, data=_image.getdata(),
                        attrib={"name": _image.name, "encoding": "base64"})

    @staticmethod
    def estimate_height(template):
        """Return estimated printout height for a section template"""
        # If the section height is explicit, return it.
        _box = template.find("box")
        if _box is None:
            _rv = 0
        else:
            _rv = Box.from_element(_box).height
        if _rv > 0:
            return _rv
        # No luck.  Find the largest vertical space
        # occupied by an inner element.
        _rv = 0
        for _element in template:
            _box = _element.find("box")
            if _box is None:
                continue
            _box = Box.from_element(_box)
            if _box.y > 0:
                _bottom = _box.y
            else:
                _bottom = 0
            if _box.height > 0:
                _bottom += _box.height
            if _bottom > _rv:
                _rv = _bottom
        return _rv

class Frame(Structure):

    """An area on the page with optional header and footer

    Example:

        +-----------------------------+
        |  A                          |
        | +-------------------------+ |
        | | headerA                 | |
        | +-------------------------+ |
        | +-----------+ +-----------+ |
        | | B1        | | B2        | |
        | |+---------+| |+---------+| |
        | || headerB || || headerB || |
        | |+---------+| |+---------+| |
           ...........   ...........
        | |+---------+| |+---------+| |
        | || footerB || || footerB || |
        | |+---------+| |+---------+| |
        | +-----------+ +-----------+ |
        | +-------------------------+ |
        | | footerA                 | |
        | +-------------------------+ |
        +-----------------------------+

    The example shows page layout with two frame definitions: A and B.
    Definition B is arranged for 2-column output (so the example shows
    two instances of this definition).

    If frame A represents the whole page then its' printable space
    is page dimensions minus sizes of the page margins.

    Printable width for frame B is (widthA-(gap*(columns-1)))/columns
    (for 2 columns that is (widthA-gap)/2).  The bottom margin for
    frame B is set to the bottom margin of frame A minus height
    of the footer placed in frame A.

    Frames are arranged in linked list: each frame keeps references
    to containing frame (parent) and contained frame (child).

    """

    # pylint: disable-msg=R0903
    # R0903: Too few public methods

    colcount = 1    # number of columns
    colgap = 0      # space between columns
    column = 0      # current column index
    x = 0           # x position for current column
    width = 0       # printable width
    top = 0         # position of the top margin
    bottom = 0      # position of the bottom margin
    header = None   # template of the header section for this frame
    footer = None   # template of the footer section for this frame
    parent = None   # containing frame
    child = None    # contained frame
    max_y = 0       # maximum y position reached at end of column

    def __repr__(self):
        if self.colcount > 1:
            _col = " (column %i/%i)" % (self.column + 1, self.colcount)
        else:
            _col = ""
        return "<%s@%X%s: %.1f, %.1f, %.1f, %.1f>" % (
            self.__class__.__name__, id(self), _col,
            self.x, self.top, self.x+self.width, self.bottom)
            # Margin positions seem to be more useful than dimensions...
            #self.x, self.top, self.width, self.height)

    @property
    def height(self):
        """Read-only height of frame"""
        return self.bottom - self.top

    def make_child(self, **kwargs):
        """Create new Frame inside this one

        Child frame attributes that are not overridden
        by keyword arguments will be initialized as follows:
            - width is copied from this frame
            - top is lowered by size of this frame header
            - bottom is raised by size of this frame footer
            - parent is set to this frame
            - all other attributes will have default values

        """
        _args = {"parent": self, "width": self.width,
            "top": self.top, "bottom": self.bottom}
        if self.header is not None:
            _args["top"] += Section.estimate_height(self.header)
        if self.footer is not None:
            _args["bottom"] -= Section.estimate_height(self.footer)
        _args.update(kwargs)
        self.child = self.__class__(**_args)
        return self.child

class Builder(object):

    """PythonReports builder

    Instances of this class apply a template to a sequence
    of report data objects producing a printout structure
    that can be serialized to XML (PRP file) and rendered
    by front-end drivers to screen, printer, PDF etc.

    """

    # An ID generator state
    gen_id = 0
    gen_id_lock = threading.Lock()
    ### following properties hold builder state.  reinitialized by each .run()
    # current page position
    cur_y = 0
    # list of output pages.  each page is a list of Section objects
    pages = []
    # current page
    page = None
    # evaluation contexts for current and previous data items
    context = old_context = None
    # group expressions, used to detect group changes
    group_values = {}
    # page number offset for each group
    group_page_offsets = {}
    # deferred evaluations.
    # keys are "report", "page", "column" or tuples ("group", name)
    # values are ReportElements with templates having the "expr"
    # attribute (fields and barcodes).
    eval_later = {}
    # report section frames
    section_frames = {}
    # for inlined reports, builders responsible for external headers/footers
    section_builders = {}
    # parent elements for report sections
    layout_parents = {}

    def __init__(self, template, data=(), parameters=None,
        item_callback=None, text_backend=None, image_backend=None,
    ):
        """Initialize builder

        Parameters:
            template: PRT file name or ElementTree
                with loaded report template
            data: report data sequence
            parameters: values for report parameters
                (dictionary or sequence of (key, value) pairs)
            item_callback: if passed, must be a callable
                that will be called without arguments
                for each item of the data sequence.
            text_backend: optional name of preferred text
                driver backend, e.g. "wx" or "Tk".
            image_backend: optional name of preferred image
                driver backend, e.g. "wx".

        """
        super(Builder, self).__init__()
        if isinstance(template, basestring):
            self.template = prt.load(template)
        else:
            self.template = template
        self.data = data
        if parameters:
            self.parameters = dict(parameters)
        else:
            self.parameters = {}
        self.callback = item_callback
        self.text_driver_factory = drivers.get_driver("Text", text_backend)
        self.image_driver_factory = drivers.get_driver("Image", image_backend)
        self.basedir = self.template.getroot().get("basedir", None)
        if not self.basedir:
            if self.template.filename:
                self.basedir = os.path.dirname(self.template.filename)
            else:
                self.basedir = os.getcwd()
        self.variables = [Variable(_item)
            for _item in self.template.variables.itervalues()]
        # subreport builders
        self.subreports = {}
        # text rendering drivers, will be re-evaluated in .run()
        self.text_drivers = {}
        # image collections:
        #   - kept in files
        self.images_filed = {}
        #   - loaded from named data elements
        self.images_named = {}
        #   - all loaded images, including named and unnamed data elements
        #       and files with embed=yes.  keyed by image data.
        self.images_loaded = {}
        #
        _layout = self.template.find("layout")
        # list of group templates
        self.groups = []
        _group = _layout.find("group")
        while _group is not None:
            self.groups.append(_group)
            _group = _group.find("group")
        # detail template
        if self.groups:
            self.detail = self.groups[-1].find("detail")
        else:
            self.detail = _layout.find("detail")
        # page origin
        self.leftmargin = _layout.get("leftmargin")
        self.topmargin = _layout.get("topmargin")
        self.create_frames()
        self.find_layout_parents()

    def __repr__(self):
        return "<%s@%x:%r>" % (self.__class__.__name__, id(self),
            os.path.basename(self.template.filename))

    @classmethod
    def generate_id(cls):
        """Return a new unique element ID string"""
        cls.gen_id_lock.acquire()
        try:
            cls.gen_id += 1
            _rv = "i%08X" % cls.gen_id
        finally:
            cls.gen_id_lock.release()
        return _rv

    def filepath(self, *path):
        """Return normalized absolute pathname

        Parameters: path components.

        Join all parameters as path components.
        If resulting path is relative, add report's basedir.
        Normalize and return resulting path.

        """
        return os.path.abspath(os.path.join(self.basedir, *path))

    def image(self, element):
        """Return an image object for report template element

        Parameters:
            element: template element of type "image".

        Return value: ImageDriver object for the image.

        """
        _type = element.get("type")
        # if "file" attribute is set, load image from file
        _file = element.get("file")
        if _file:
            _file = self.filepath(_file)
            try:
                return self.images_filed[_file]
            except KeyError:
                _image = self.image_driver_factory.fromfile(_file, _type)
                self.images_filed[_file] = _image
                if element.get("embed"):
                    self.images_loaded[_image.getdata(_type)] = _image
                return _image
        # try named data block
        _name = element.get("data")
        if _name:
            try:
                return self.images_named[_name]
            except KeyError:
                # lookup is separated from conversion
                # to have clearly identifiable error source
                # when _name is not in the datablocks collection.
                _imgdata = self.template.datablocks[_name]
                _img_contents = prt.Data.get_data(_imgdata, self.context)
                _image = self.image_driver_factory.fromdata(
                    _img_contents, img_type=_type, name=_name)
                # cache named images unless data is dynamic
                if not _imgdata.get("expr"):
                    self.images_named[_name] = _image
                self.images_loaded[_img_contents] = _image
                return _image
        # unnamed data block (child of the image element)
        _data = element.find("data")
        if _data is None:
            _image = self.image_driver_factory.nullimage()
            _imgdata = _image.getdata()
            if _imgdata not in self.images_loaded:
                self.images_loaded[_imgdata] = _image
        else:
            _imgdata = prt.Data.get_data(_data, self.context)
            if _imgdata not in self.images_loaded:
                _image = self.image_driver_factory.fromdata(_imgdata,
                    img_type=_type)
                self.images_loaded[_imgdata] = _image
        return self.images_loaded[_imgdata]

    def find_layout_parents(self):
        """Register parent sections for all sections of the template"""
        _layout = self.template.find("layout")
        self.layout_parents = {_layout: None}
        _descend = [_layout]
        while _descend:
            _next_level = []
            for _item in _descend:
                for _child in self.template.getchildren(_item):
                    if _child.tag in ("group", "columns"):
                        _next_level.append(_child)
                    if _child.tag in (
                        "title", "summary", "header", "footer",
                        "columns", "group", "detail",
                    ):
                        self.layout_parents[_child] = _item
            _descend = _next_level

    def create_frames(self):
        """Create frames for all report sections"""
        _layout = self.template.find("layout")
        self.section_frames = {}
        # page frame, used for page header/footer and swapped title/summary
        _page_frame = Frame()
        (_page_frame.width, _page_frame.bottom) = \
            self.get_page_dimensions(self.template)
        _page_frame.width -= _layout.get("leftmargin") \
            + _layout.get("rightmargin")
        _page_frame.bottom -= _layout.get("bottommargin")
        # keep the outermost frame under well-known key
        self.section_frames[None] = _page_frame
        # create inner frames for each header/footer pair
        _frame = _page_frame
        _headers = _layout.findall("header")
        _footers = _layout.findall("footer")
        _footers.reverse()
        if len(_headers) > len(_footers):
            _footers.extend((None,) * (len(_headers) - len(_footers)))
        elif len(_footers) > len(_headers):
            _headers.extend((None,) * (len(_footers) - len(_headers)))
        for (_header, _footer) in zip(_headers, _footers):
            _frame.header = _header
            _frame.footer = _footer
            if _header is not None:
                self.section_frames[_header] = _frame
            if _footer is not None:
                self.section_frames[_footer] = _frame
            _frame = _frame.make_child()
        # add title and summary
        # if swapped, they use page frame, otherwise inner frame
        _section = _layout.find("title")
        if _section is not None:
            if _section.get("swapheader") and _section.find("eject"):
                self.section_frames[_section] = _page_frame
            else:
                self.section_frames[_section] = _frame
        _section = _layout.find("summary")
        if _section is not None:
            if _section.get("swapfooter"):
                self.section_frames[_section] = _page_frame
            else:
                self.section_frames[_section] = _frame
        # create toplevel columns frame
        _frame = self.make_column_frames(_layout, _frame)
        # process all groups
        for _group in self.groups:
            # group title and summary use containing frame, columns are inside
            _title = _group.find("title")
            if _title is not None:
                self.section_frames[_title] = _frame
            _summary = _group.find("summary")
            if _summary is not None:
                self.section_frames[_summary] = _frame
            _frame = self.make_column_frames(_group, _frame)
        # detail section uses innermost frame
        self.section_frames[self.detail] = _frame

    def make_column_frames(self, group, parent_frame):
        """Create frames for columns definition

        Parameters:
            group: data group or layout template element
            parent_frame: containing frame

        Return the frame to use for contents

        """
        _columns = group.find("columns")
        if _columns is None:
            return parent_frame
        _colcount = _columns.get("count")
        _colgap = _columns.get("gap")
        _width = (parent_frame.width - ((_colcount - 1) * _colgap)) / _colcount
        _frame = parent_frame.make_child(width=_width,
            colcount=_colcount, colgap=_colgap)
        self.section_frames[_columns] = _frame
        _header = _columns.find("header")
        _footer = _columns.find("footer")
        if not ((_header is None) and (_footer is None)):
            if _header is not None:
                self.section_frames[_header] = _frame
                _frame.header = _header
            if _footer is not None:
                self.section_frames[_footer] = _frame
                _frame.footer = _footer
            _inner_frame = _frame.make_child()
        else:
            _inner_frame = _frame
        return _inner_frame

    def run(self, data=NOTHING, parameters=None, item_callback=None):
        """Build the report

        Parameters:
            data: optional data sequence.  If passed, overrides
                the sequence passed to builder initialization.
            parameters: optional values for report parameters (dictionary).
                combined with parameters passed to initialization.
            item_callback: optional callable to be called for each
                data item.  If passed, overrides the callback
                passed to initialization.

        Return value: Printout object

        """
        # Timings: for 1000 items of test data,
        # processing takes about 10s
        # and output generation takes about .4s
        #_start_time = time.time()
        if item_callback:
            _callback = item_callback
        else:
            _callback = self.callback
        _data_iter = self.start(data, parameters)
        self._build(_data_iter, _callback)
        #print "built in %.2fs" % (time.time() - _start_time)
        return self.build_printout()

    def _build(self, data, callback=None):
        """Build output page structures

        Parameters:
            data: data sequence iterator.  Normally, the first item
                is already popped from this iterator to current context
                when this method is called.
            callback: a callable to be called for each data item.

        """
        if callback:
            callback()
        self.fill_title()
        # first item was already popped out of _data_iter
        # (for use in title/headers context).  print it out now.
        if self.context["THIS"] is not None:
            self.fill_detail()
        # process remaining items
        for _item in data:
            self.next_item(_item)
            if callback:
                callback()
            self.fill_detail()
        # fill_summary will close all report groups.
        # since group summaries are always evaluated in old_context
        # (assuming that current context started a new group)
        # we now need old_context to be current context.
        self.old_context = self.context
        self.fill_summary()
        # resolve all deferred evaluations
        self.resolve_eval(*self.eval_later.keys())

    def start(self, data=NOTHING, parameters=None):
        """Initialize report building

        Parameters:
            data: optional data sequence.  If passed, overrides
                the sequence passed to builder initialization.
            parameters: optional values for report parameters (dictionary).
                combined with parameters passed to initialization.

        Create initial context, initialize all report structures,
        start the first page (without any content).

        Return value: data sequence iterator (with the first
        object already iterated out; available in context["THIS"]).

        """
        _template = self.template
        # initialize fonts - moved from __init__() to allow backend switching
        self.text_drivers = dict([(_name, self.text_driver_factory(_font))
            for (_name, _font) in _template.fonts.iteritems()])
        # create data iterator and get the first object, if any
        if data is NOTHING:
            _data = self.data
        else:
            _data = data
        _data_iter = iter(_data)
        try:
            _data_obj = _data_iter.next()
        except StopIteration:
            _data_obj = None
        # build initial context:
        # initialize counters for all report groups,
        # set row object and total length of data
        _group_names = [_item.get("name") for _item in self.groups]
        _context = Context(sysvars=dict(
            [("DATA_COUNT", len(_data)), ("THIS", _data_obj)]
            + [(_name + "_COUNT", 0) for _name in _group_names]
            + [(_name + "_PAGE_NUMBER", 0) for _name in _group_names]
        ))
        _context.add_variables(*self.variables)
        _context.load_imports(_template)
        # collect report parameters
        _parameters = dict(self.parameters)
        if parameters:
            _parameters.update(parameters)
        for (_name, _parm) in _template.parameters.iteritems():
            if _name not in _parameters:
                _value = _context.eval(_parm.get("default"), _parm)
                if _parm.get("prompt", False):
                    # TODO? parameter input with wx or Tkinter GUI
                    _input = raw_input("%s [%s]: " % (_name, _value))
                    if _input:
                        _value = _input
                _parameters[_name] = _value
        _context.parameters = _parameters
        self.context = self.old_context = _context
        # initialize build structures
        self.pages = []
        self.eval_later = dict([(_key, [])
            for _key in ["report", "page", "column"]
                + [("group", _name) for _name in _group_names]
        ])
        self.group_page_offsets = dict.fromkeys(_group_names, 0)
        # initialize all variables
        for _item in self.variables:
            _item.start(_context)
            if _item.iter in ("report", "item"):
                _item.iterate(_context)
        # initialize group expressions
        for _item in self.groups:
            self.group_values[_item.get("name")] = _context.eval(
                _item.get("expr"), _item)
        # create the first page
        self.start_page()
        return _data_iter

    def next_item(self, data):
        """Prepare for processing of the next item in report data sequence

        Parameters:
            data: data object

        Build new context, check all group expressions
        and end/start groups if any expression is changed.

        Note: this does not increment *_COUNT variables -
        that will be done in .fill_detail() if the detail
        section is printable.

        """
        _context = self.context
        self.old_context = _context.copy()
        #self.old_context.freeze()
        _context["THIS"] = data
        _context["ITEM_NUMBER"] += 1
        _groups_changed = []
        for (_idx, _group) in enumerate(self.groups):
            _group_name = _group.get("name")
            _value = _context.eval(_group.get("expr"), _group)
            if not (_value == self.group_values[_group_name]):
                # group change implies change of all inner groups
                _groups_changed = self.groups[_idx:]
                # save new value and reeval remaining groups
                self.group_values[_group_name] = _value
                for _group in _groups_changed[1:]:
                    self.group_values[_group.get("name")] = _context.eval(
                        _group.get("expr"), _group)
                break
        # output group summaries, see if any of changed groups
        # start with a column or page eject.
        _eject = None
        for _group in reversed(_groups_changed):
            self.end_group(_group)
            if (_eject == "column") and _group.find("columns"):
                # The columns end here.  No eject after this group's summary.
                _eject = None
            _first_section = _group.find("title")
            if _first_section is None:
                _first_section = _group.find("detail")
            if _first_section is None:
                # The first of the following sections
                # belongs to an embedded group, won't eject here.
                continue
            _eject = self.need_eject(_first_section)
            if _eject == "page":
                break
        if _eject:
            _eject_frames = self.get_eject_frames(
                self.section_frames[self.detail],
                newpage=(_eject == "page"))
            # Build all footers in the context of the previous item
            self.context = self.old_context
            self.eject_print_footers(_eject_frames)
            self.context = _context
        else:
            _eject_frames = []
        for _group in reversed(_groups_changed):
            self.resolve_eval(("group", _group.get("name")))
        for _var in self.variables:
            if _var.reset == "item":
                _var.start(_context)
            if _var.iter == "item":
                _var.iterate(_context)
        for _group in _groups_changed:
            self.iterate_group_variables(_group)
        if _eject:
            _eject_frames.reverse()
            self.eject_print_headers(_eject_frames)
        for _group in _groups_changed:
            self.start_group(_group)

    def fill_title(self):
        """Build the beginning of the report

        Fill report title, page header, all group and column headings.

        """
        _layout = self.template.find("layout")
        _layout_title = _layout.find("title")
        if _layout_title is None:
            self.fill_initial_headers()
        else:
            if _layout_title.get("swapheader"):
                _section = self.build_section(_layout_title)
                if _section is not None:
                    self.add_section(_section)
                    self.check_eject(_layout_title, ignoresize=True)
                # XXX Not good.
                # If a page is ejected by .fill_initial_headers(),
                # we get overlapping content in self.pages
                # and in containing builder.
                self.fill_initial_headers()
            else:
                self.fill_initial_headers()
                _section = self.build_section(_layout_title)
                if _section is not None:
                    self.add_section(_section)
                    self.check_eject(_layout_title, ignoresize=True)
        self.add_section(self.build_section(_layout.find("columns/header")))
        for _group in self.groups:
            self.start_group(_group)

    def fill_detail(self):
        """Build a detail section

        Eject column/page if requested, create detail section
        and put it on the current page (column) if there is enough
        space.  If not, eject and rebuild the detail section at new
        page or column.

        """
        _template = self.detail
        self.check_eject(_template)
        # create new context with incremented *_COUNT values
        _new_context = self.context.copy()
        for _name in _new_context.sysvars:
            if _name.endswith("_COUNT") and (_name != "DATA_COUNT"):
                _new_context[_name] += 1
        for _var in self.variables:
            if _var.reset == "detail":
                _var.start(_new_context)
                if _var.iter == "item":
                    _var.iterate(self.context)
            if _var.iter == "detail":
                _var.iterate(_new_context)
        # apply new context.
        # keep current context for a while for possible rollback
        _current_context = self.context
        self.context = _new_context
        # build the section
        _section = self.build_section(_template)
        if _section is not None:
            # place the section
            self.add_section(_section)
        else:
            # the section is not printed - undo context changes
            self.context = _current_context
            for _var in self.variables:
                if _var.reset == "detail":
                    # reinitialize with context rolled back
                    _var.start(self.context)
                    if _var.iter == "item":
                        _var.iterate(self.context)
                elif _var.iter == "detail":
                    _var.rollback()

    def fill_summary(self):
        """Build the end of the report

        Fill all group and column footers, report summary and page footer.

        """
        _layout = self.template.find("layout")
        for _group in reversed(self.groups):
            self.end_group(_group)
            self.resolve_eval(("group", _group.get("name")))
        _columns = _layout.find("columns")
        if _columns is not None:
            self.add_section(self.build_section(_columns.find("footer")))
            self.resolve_eval("column")
            _max_y = self.section_frames[_columns].max_y
            if _max_y > self.cur_y:
                self.cur_y = _max_y
        _summary = _layout.find("summary")
        # will build footers from own template only
        _inline = bool(self.section_builders)
        _layout_footers = tuple(_section
            for _section in _layout.findall("footer")
            if not (_inline and (_section in self.section_builders)))
        if _summary is None:
            # Note: if this report is inlined, we build only own footers;
            # master page footer will be built by containing template
            # builder, and would be placed at the bottom of page.
            self.fill_footers(_layout_footers, _inline)
        else:
            self.check_eject(_summary)
            if _summary.get("swapfooter") and (_footer is not None):
                self.fill_footers(_layout_footers, _inline)
                self.add_section(self.build_section(_summary))
            else:
                self.add_section(self.build_section(_summary))
                self.fill_footers(_layout_footers, _inline)

    def fill_footers(self, templates, inline=False, context=None):
        """Fill a sequence of column/page footers

        Build footer sections from passed template list,
        reposition them if needed, and add new sections
        to the printout.

        At the end of the report a footer may be repositioned
        immediately after the report contents (rather than being
        printed at the bottom of the page) in two cases:

            * There is report summary with "swapfooter" flag.

            * This report is inlined (containing report will
              continue on the same page).

        If inline argument evaluates to boolean True, the sections
        are placed at current page position (reposition not needed).

        Otherwise the sections are repositioned at the bottom
        of the outermost frame, immediately above one another.

        """
        _footers = []
        _page_footers = []
        _column_footers = []
        for _footer in templates:
            _section = self.build_section(_footer, context)
            if _section:
                _frame = self.section_frames[_footer]
                _footers.append((_section, _frame))
                if _frame.colcount == 1:
                    _page_footers.append(_section)
                else:
                    _column_footers.append(_section)
        # move page footers to the bottom of the page unless inlined
        if _page_footers and not inline:
            _bottom = _footers[-1][1].bottom
            _cur_y = max(
                sum((_footer.box.height for _footer in _column_footers),
                    self.cur_y),
                _bottom - sum(_footer.box.height for _footer in _page_footers))
            for _footer in _page_footers:
                _footer.refill(_cur_y)
                _cur_y += _footer.box.height
        for (_footer, _frame) in _footers:
            if _footer.box.y < _frame.bottom:
                self.add_section(_footer)
                # Adjust maximum used column length for containing frame.
                _frame = self.section_frames[_footer.template]
                if _footer.box.bottom > _frame.max_y:
                    _frame.max_y = _footer.box.bottom

    def fill_initial_headers(self):
        """Create all page headers at the start of report

        If there is not enough space to fit all headers
        up to the detail section on current page,
        eject on the innermost containing builder.

        """
        _headers = []
        _hsize = Section.estimate_height(self.detail)
        for _template in self.template.findall("layout/header"):
            if _template not in self.section_builders:
                _section = self.build_section(_template)
                _headers.append((_template, _section))
                _hsize += _section.box.height
        _avail = self.section_frames[self.detail].bottom - self.cur_y
        if _hsize < _avail:
            # All built headers would fit here - put them in and return
            for (_template, _section) in _headers:
                self.add_section(_section)
            return
        # Find innermost containing frame
        _top = -1
        _bottom = 1e6
        _eject_frame = None
        for _section in self.section_builders:
            _frame = self.section_frames[_section]
            if _frame.top > _top:
                _top = _frame.top
                _eject_frame = _frame
            elif _frame.bottom < _bottom:
                _bottom = _frame.bottom
                _eject_frame = _frame
        if _eject_frame is None:
            # No containing frame found
            self.start_page()
        else:
            self.eject(_eject_frame, newpage=True)
        for (_template, _junk) in _headers:
            self.add_section(self.build_section(_template))

    def is_page_filled(self):
        """Return True when there are non-empty sections on current page"""
        if not self.page:
            return False
        for _section in self.page:
            if _section:
                return True
        return False

    def start_page(self):
        """Create new output page

        Create new page object, add it to the pages list
        and set self.page to this new object.  Update
        context variables and current output position.

        Note: builder's page is just a list of Section objects.

        When current page is initialized but empty, do nothing.

        """
        if self.pages and not self.is_page_filled():
            # Avoid ejects on empty pages
            return
        self.page = []
        self.pages.append(self.page)
        self.cur_y = self.topmargin
        self.context["PAGE_NUMBER"] += 1
        self.context["PAGE_COUNT"] = 0
        self.context["COLUMN_COUNT"] = 0
        for (_name, _offset) in self.group_page_offsets.iteritems():
            self.context[_name + "_PAGE_NUMBER"] \
                = self.context["PAGE_NUMBER"] - _offset
        # reset column index for all frames
        _frame = self.section_frames[None]
        while _frame:
            _frame.column = 0
            _frame.max_y = self.cur_y
            _frame.x = self.leftmargin
            _frame = _frame.child
        # reset/iterate variables
        for _var in self.variables:
            if _var.reset in ("page", "column"):
                _var.start(self.context)
                if _var.iter == "item":
                    _var.iterate(self.context)
            if _var.iter in ("page", "column"):
                _var.iterate(self.context)

    def iterate_group_variables(self, group):
        """Iterate all group-based variables at the start of a data group"""
        _group_name = group.get("name")
        self.context["%s_COUNT" % _group_name] = 0
        for _var in self.variables:
            if (_var.reset == "group") and (_var.resetgrp == _group_name):
                _var.start(self.context)
                if _var.iter == "item":
                    _var.iterate(self.context)
            if (_var.iter == "group") and (_var.itergrp == _group_name):
                _var.iterate(self.context)

    def start_group(self, group):
        """Start a data group

        Print group title and column header (if any).

        """
        _group_name = group.get("name")
        self.group_page_offsets[_group_name] = self.context["PAGE_NUMBER"] - 1
        self.context[_group_name + "_PAGE_NUMBER"] = 1
        _title = group.find("title")
        if _title is not None:
            self.check_eject(_title)
            self.add_section(self.build_section(_title))
        _columns = group.find("columns")
        if _columns is not None:
            self.add_section(self.build_section(_columns.find("header")))

    def end_group(self, group):
        """End a data group

        Print column footer and group summary (if any).

        """
        _columns = group.find("columns")
        if _columns is not None:
            self.add_section(self.build_section(_columns.find("footer"),
                context=self.old_context))
            _max_y = self.section_frames[_columns].max_y
            if _max_y > self.cur_y:
                self.cur_y = _max_y
        _summary = group.find("summary")
        if _summary is not None:
            self.check_eject(_summary)
            self.add_section(self.build_section(_summary,
                context=self.old_context))

    def set_page_position(self, ypos):
        """Set current y position on the output page

        Parameters:
            ypos: new position in points.

        All output frames are adjusted to start output below given position.

        """
        self.cur_y = ypos
        _frame = self.section_frames[None].child
        while _frame:
            _frame.top = ypos
            _frame = _frame.child

    def build_embedded_template(self, element):
        """Return a template ElementTree for embedded subreport

        Embedded subreports use imports, fonts, named data blocks,
        and page layout parameters from the main template.

        Build a complete Template ElementTree for a subreport
        from a combination of own template parts and the element contents.

        """
        _this_root = self.template.getroot()
        _new_root = self.template.copy(_this_root)
        # Make a shallow copy of all top-level elements.
        for _elem in self.template.getchildren(_this_root):
            if _elem.tag in ("import", "font", "data", "layout"):
                _new_root.append(self.template.copy(_elem))
        _new_layout = _new_root.find("layout")
        for _elem in self.template.getchildren(element):
            if _elem.tag in ("parameter", "variable"):
                _new_root.insert(0, self.template.copy(_elem))
            else:
                _new_layout.append(_elem)
        _rv = ElementTree(self.template.root_validator, _new_root)
        _rv.filename = self.template.filename
        _rv.validate()
        return _rv

    def get_subreport_builder(self, element):
        """Return a Builder object for a subreport element

        Parameters:
            element: a "subreport" element from the report template

        Return: tuple (is_inline, builder)

        """
        _embedded = element.get("embedded")
        _is_inline = bool(_embedded or element.get("inline"))
        if element in self.subreports:
            return (_is_inline, self.subreports[element])
        _this_layout = self.template.find("layout")
        if _embedded:
            _prt = self.build_embedded_template(
                self.template.embedded[_embedded])
            _layout = _prt.find("layout")
        else:
            _prt_name = element.get("template")
            _prt = prt.load(self.filepath(_prt_name))
            if _is_inline:
                # inlined report must have same page dimensions as this report
                _pgsize = self.get_page_dimensions(self.template)
                if self.get_page_dimensions(_prt) != _pgsize:
                    raise XmlValidationError(
                        "Page size does not match for inlined report \"%s\""
                        % _prt_name, element=element)
                _layout = _prt.find("layout")
                assert _layout is not None # _prt is verified
                _MARGIN_ATTRS = ("leftmargin", "topmargin",
                    "rightmargin", "bottommargin")
                _margins = tuple(tuple(_section.get(_margin, 0)
                    for _margin in _MARGIN_ATTRS)
                    for _section in (_layout, _this_layout))
                if _margins[0] != _margins[1]:
                    warn(XmlValidationWarning("Overriding page margins"
                        " for subreport %s: (%s) => (%s)" % ((_prt_name,)
                        + tuple(", ".join(map(str, _margin))
                            for _margin in _margins)),
                        element=_layout))
                    for (_name, _value) in zip(_MARGIN_ATTRS, _margins[1]):
                        _layout.set(_name, _value)
            else:
                _builder = Builder(_prt)
        if _is_inline:
            # Insert page headers and footers from own template.
            # Actual rendering will be done by responsible builders,
            # but subreport builder will need to know sizes
            # to shrink page contents frame appropriately.
            _page_frame = self.section_frames[None]
            _outer_sections = _this_layout.findall("footer")
            if sys.version_info[:2] < (2, 7):
                # _ElementInterface instance has no attribute 'extend'
                for _section in _outer_sections:
                    _layout.append(_section)
            else:
                _layout.extend(_outer_sections)
            for _section in reversed(_this_layout.findall("header")):
                _layout.insert(0, _section)
                _outer_sections.append(_section)
            # create subreport builder
            _builder = Builder(_prt)
            # copied sections must be built by outer builders
            if _outer_sections:
                _builder.section_builders = dict(
                    (_section, self.section_builders.get(_section, self))
                    for _section in _outer_sections)
        self.subreports[element] = _builder
        return (_is_inline, _builder)

    def run_subreport(self, element, eject_frame):
        """Execute a subreport element

        Parameters:
            element: template element for subreport to run
            eject_frame: if running of a non-inlined subreport
                must terminate current page in the master report,
                this is output frame for current report section.
                If current page was already ejected, eject_frame is None.

        Return value: if this run did page eject in the main report,
        return None.  Otherwise return the value of eject_frame argument.

        """
        _context = self.context
        # return early if subreport is skipped
        _when = element.get("when")
        if _when and not _context.eval(_when, element):
            return eject_frame
        # return early if there are no data items for the subreport
        _data = _context.eval(element.get("data"), element)
        if len(_data) < 1:
            return eject_frame
        (_inline, _builder) = self.get_subreport_builder(element)
        # collect subreport arguments
        # Note: this is done before any new section is built
        #       to make sure current build context is not changed and
        #       our local short-cut (_context variable) is still valid.
        _args = {}
        for _item in element.findall("arg"):
            _args[_item.get("name")] = _context.eval(_item.get("value"), _item)
        # check if we need to eject page
        if _inline or (eject_frame is None):
            _rv = eject_frame
        else:
            # print all footers, end current page
            _eject_frames = self.get_eject_frames(eject_frame, True)
            for _frame in _eject_frames:
                self.add_section(self.build_section(_frame.footer))
            self.resolve_eval("page", "column")
            # reset output value
            _rv = None
            # advance page number if it will be
        # run the subreport
        _data_iter = _builder.start(_data, _args)
        if _inline:
            _builder.context["PAGE_NUMBER"] = self.context["PAGE_NUMBER"]
            _builder.set_page_position(self.cur_y)
        elif not element.get("ownpageno"):
            _builder.context["PAGE_NUMBER"] = self.context["PAGE_NUMBER"] + 1
        _builder._build(_data_iter)
        if _inline:
            self.context["PAGE_NUMBER"] = _builder.context["PAGE_NUMBER"]
            self.set_page_position(_builder.cur_y)
            self.page.extend(_builder.pages[0])
            self.pages.extend(_builder.pages[1:])
            self.page = self.pages[-1]
        else:
            if not element.get("ownpageno"):
                # will be incremented by .start_page()
                self.context["PAGE_NUMBER"] = _builder.context["PAGE_NUMBER"]
            if self.pages[-1] == []:
                del self.pages[-1]
            self.pages.extend(_builder.pages)
        return _rv

    def run_subreport_collection(self, subreports, current_frame):
        """Run a set of subreports for a report section

        Parameters:
            subreports: a sequence of subreport elements to run
            current_frame: layout frame for current output section

        """
        _frame = current_frame
        for _item in subreports:
            _frame = self.run_subreport(_item, _frame)
        if _frame is None:
            # current page was ejected by subreport
            self.start_page()
            _eject_frames = self.get_eject_frames(current_frame, True)
            # headers go in reverse order
            _eject_frames.reverse()
            # print all headers
            for _frame in _eject_frames:
                self.add_section(self.build_section(_frame.header))

    def build_section(self, template, context=None):
        """Build, fill and return Section object

        Parameters:
            template: PRT section object
            context: optional expression evaluation context
                if omitted, use current context

        Return value: Section object or None if the section
        is not printable (suppressed by printwhen expression).

        If the section is printable, subreports set to print
        before the section contents are run prior to building
        the section.

        """
        if template is None:
            return None
        if context is None:
            _context = self.context
        else:
            _context = context
        # if this report is inlined, some headers and footers
        # may be built by containing report builder
        _builder = self.section_builders.get(template, None)
        if _builder:
            _builder.context["PAGE_NUMBER"] = _context["PAGE_NUMBER"]
            _builder.set_page_position(self.cur_y)
            _rv = _builder.build_section(template)
            self.set_page_position(_builder.cur_y)
            # page number should not change
            return _rv
        _frame = self.section_frames[template]
        _context["COLUMN_NUMBER"] = _frame.column + 1
        _context["VERTICAL_POSITION"] = self.cur_y
        _context["VERTICAL_SPACE"] = _frame.bottom - self.cur_y
        _section = Section(self, template, _context)
        if not _section.printable:
            return None
        if _section.subreports_before:
            self.run_subreport_collection(_section.subreports_before, _frame)
            # reevaluate the section
            # NB: this discards the context passed in arguments
            _context = self.context
            _context["VERTICAL_POSITION"] = self.cur_y
            _context["VERTICAL_SPACE"] = _frame.bottom - self.cur_y
            _section.build(_context)
            if not _section.printable:
                # oops!
                return None
        _section.fill(_frame.x, self.cur_y, _frame.width, _frame.bottom)
        if ((_section.box.y + _section.box.height) > _frame.bottom) \
        and (_section.template.tag not in ("header", "footer")):
            self.eject(_frame)
            _context["COLUMN_NUMBER"] = _frame.column + 1
            _context["VERTICAL_POSITION"] = self.cur_y
            _context["VERTICAL_SPACE"] = _frame.bottom - self.cur_y
            _section.build(_context)
            if not _section.printable:
                return None
            _section.fill(_frame.x, self.cur_y, _frame.width, _frame.bottom)
        return _section

    def add_section(self, section):
        """Add a filled section to current page, run trailing subreports

        Parameters:
            section: filled Section object
                if None, this method is no-op

        Note: this method is separated from .build_section()
        to allow the caller to check if the section fits into
        current page.

        """
        if section is None:
            return
        # TODO? if the section is empty (no content), simply advance cur_y
        # without adding the section to the page
        self.page.append(section)
        self.cur_y = section.box.y + section.box.height
        # adjust top margin of all contained frames
        # (new columns will start at this position)
        #
        # updating just one direct child is not enough:
        #
        # +-1-------------+
        # |    header     |
        # |+-2-----------+|
        # ||+-3--+ +-3--+||
        #
        # we added header of frame 1.  its' direct child
        # is frame 2, which contains no own sections but
        # a child frame arranged for multi-column output.
        # to have correct position after eject of frame 3
        # we must update all embedded frames recursively.
        # (perhaps just a grandchild would be enough too?)
        #
        _frame = self.section_frames[section.template].child
        while _frame:
            _frame.top = self.cur_y
            _frame = _frame.child
        if section.subreports_after:
            self.run_subreport_collection(section.subreports_after,
                self.section_frames[section.template])

    def need_eject(self, section, ignoresize=False):
        """Return an eject requested by report template section

        Parameters:
            section: template section
            ignoresize: if True, don't eject when section height
                is greater than remaining available space
                (used to eject *after* report title section)

        Return "page" or "column" when an eject is required.
        Otherwise return None.

        """
        _current_frame = self.section_frames[section]
        _avail = _current_frame.bottom - self.cur_y
        _eject = None
        for _item in section.findall("eject"):
            _when = _item.get("when")
            if _when and not self.context.eval(_when, _item):
                # disabled
                continue
            _when = _item.get("require")
            if (_when is None) or (_avail < _when):
                # eject criteria met
                _eject = _item.get("type")
            # according to docs, the search stops at the first match
            break
        if not (_eject or ignoresize):
            # check if there is enough space for the section box
            _box = Box.from_element(section.find("box"))
            if (_box.y + _box.height) > _avail:
                _eject = "column"
        return _eject

    def check_eject(self, section, ignoresize=False):
        """Eject page/column if requested by report template

        Parameters:
            section: template section
            ignoresize: if True, don't eject when section height
                is greater than remaining available space
                (used to eject *after* report title section)

        """
        _eject = self.need_eject(section, ignoresize)
        if _eject:
            self.eject(self.section_frames[section], _eject=="page")

    def get_eject_frames(self, current_frame, newpage):
        """Return a list of frames affected by eject

        Parameters:
            current_frame: frame for a section that caused eject
            newpage: if True, eject page, otherwise eject column.

        Return value: list containing all frames that should have
        their headers/footers printed by requested eject type.
        The list starts with current_frame and contains it's parents
        ending with a column or page frame.

        """
        # build a list of all frames that will have their
        # headers/footers printed by this eject
        _eject_frames = []
        if newpage:
            # build footers/headers for current frame and all parents
            _frame = current_frame
            while _frame:
                _eject_frames.append(_frame)
                _frame = _frame.parent
        else:
            # if we are starting new column but this is the last column
            # of the current frame eject parents recursively
            _frame = current_frame
            while _frame:
                _eject_frames.append(_frame)
                if _frame.column < (_frame.colcount - 1):
                    # this frame can make another column -
                    # it is the last frame to eject
                    break
                _frame = _frame.parent
        return _eject_frames

    def eject_print_footers(self, eject_frames):
        """Output all footer sections before a page or column eject"""
        self.fill_footers(tuple(
            _frame.footer for _frame in eject_frames
            if _frame.footer is not None
        ), context=self.old_context)

    def eject_print_headers(self, eject_frames):
        """Output all header sections after a page or column eject"""
        # if last ejected was page footer, start new page
        # otherwise reset column index for all column frames
        # except the last one
        _frame = eject_frames[0]
        if _frame is self.section_frames[None]:
            self.resolve_eval("page", "column")
            self.start_page()
        else:
            self.resolve_eval("column")
            self.context["COLUMN_COUNT"] = 0
            # reset/iterate column-based variables
            for _var in self.variables:
                if _var.reset == "column":
                    _var.start(self.context)
                    if _var.iter == "item":
                        _var.iterate(self.context)
                if _var.iter == "column":
                    _var.iterate(self.context)
            # change page position to the top of new column
            self.cur_y = _frame.top
            _frame.column += 1
            _xpos = _frame.parent.x \
                + ((_frame.width + _frame.colgap) * _frame.column)
            _frame.x = _xpos
            # all inner frames are at the first column
            for _frame in eject_frames[1:]:
                _frame.x = _xpos
                _frame.column = 0
        # print all headers
        for _frame in eject_frames:
            self.add_section(self.build_section(_frame.header))

    def eject(self, current_frame, newpage=False):
        """Eject page or column

        Parameters:
            current_frame: frame for a section that caused eject
            newpage: if True, eject page.
                Otherwise eject column (default).

        """
        # build a list of all frames that will have their
        # headers/footers printed by this eject
        _eject_frames = self.get_eject_frames(current_frame, newpage)
        self.eject_print_footers(_eject_frames)
        # headers will go in reverse order: first for the last footer printed
        _eject_frames.reverse()
        self.eject_print_headers(_eject_frames)

    def register_eval(self, element):
        """Register deferred evaluation for element expression

        Parameters:
            element: ReportElement having template with non-empty evaltime

        """
        _template = element.template
        _evaltime = _template.get("evaltime")
        if not _evaltime:
            # eh?
            return
        if _evaltime not in ("report", "page", "column"):
            _evaltime = ("group", _evaltime)
        self.eval_later[_evaltime].append(element)

    def resolve_eval(self, *args):
        """Resolve deferred evaluations and refill corresponding sections

        Parameters are keys to deferred evaluations registry.

        Expressions are evaluated in the previous evaluation context.

        """
        # _refill collection contains unique sections.
        # it would be a set if section objects are hashable.
        # but they are not, so use a dictionary keyed by section ids.
        _refill = {}
        for _key in args:
            for _element in self.eval_later[_key]:
                _template = _element.template
                _value = self.old_context.eval(
                    _template.get("expr"), _template)
                _element.text = _template.get("format", u"%s") % _value
                _refill[id(_element.section)] = _element.section
            self.eval_later[_key] = []
        for _section in _refill.itervalues():
            _section.refill()

    @staticmethod
    def get_page_dimensions(template):
        """Return (width, height) for output page

        Parameters:
            template: verified report template tree.

        """
        _layout = template.find("layout")
        _pagesize = _layout.get("pagesize")
        if _pagesize:
            (_width, _height) = _pagesize.dimensions
        else:
            _width = _layout.get("width")
            _height = _layout.get("height")
        if _layout.get("landscape"):
            (_width, _height) = (_height, _width)
        return (_width, _height)

    def collect_fonts(self):
        """Collect font elements from self and all processed subreports

        Return dictionary where keys are font names
        and values are tree elements.

        """
        _all_fonts = dict((_item.get("name"), _item)
            for _item in self.template.findall("font"))
        for (_element, _builder) in self.subreports.iteritems():
            for (_name, _font) in _builder.collect_fonts().iteritems():
                _own_font = _all_fonts.get(_name, None)
                if _own_font is None:
                    _all_fonts[_name] = _font
                elif _font.attrib != _own_font.attrib:
                    raise XmlValidationError("Conflicting font definition"
                        " \"%s\" in template \"%s\""
                        % (_name, _element.get("template")),
                        element=_element)
        return _all_fonts

    def build_printout(self):
        """Create and return Printout object for built report"""
        _template = self.template.getroot()
        _attrs = dict([(_name, _template.get(_name)) for _name in
            (set(prt.Report.attributes) & set(prp.Printout.attributes))])
        # TODO: _attrs["built"] = datetime.utcnow()
        _root = Element(prp.Printout.tag, _attrs)
        _fonts = self.collect_fonts()
        for _name in sorted(_fonts):
            SubElement(_root, "font", _fonts[_name].attrib)
        # output data blocks that were not used by the builder
        # (images will be processed separately)
        _data_names = set(self.images_named)
        for (_name, _item) in self.template.datablocks.iteritems():
            if _name not in self.images_named:
                SubElement(_root, "data", _item.attrib).text = _item.text
                _data_names.add(_name)
        _img_idx = 0
        for _image in self.images_loaded.itervalues():
            # look if an unnamed image is used more than once.
            # if yes, assign it a surrogate name.
            if (_image.use_count > 1) and not _image.name:
                while True:
                    _img_idx += 1
                    _name = "Image%s" % _img_idx
                    if _name not in _data_names:
                        _image.name = _name
                        _data_names.add(_name)
                        break
            # if image data has a name, build data block
            if _image.name:
                # image data is converted to preferred type
                # and stored in base64, without compression
                # (both preferred types are compressed per se).
                prp.Data.make_element(_root, data=_image.getdata(),
                    attrib={"name": _image.name, "encoding": "base64"})
        # use layout element for page dimensions
        _layout = _template.find("layout")
        _page_attrs = dict([(_name, _layout.get(_name)) for _name in
            ("leftmargin", "topmargin", "rightmargin", "bottommargin")])
        (_page_attrs["width"], _page_attrs["height"]) = \
            self.get_page_dimensions(_template)
        for _page in self.pages:
            _prt_page = SubElement(_root, prp.Page.tag, _page_attrs)
            for _section in _page:
                _section.output(_prt_page)
        _rv = ElementTree(prp.Printout, _root)
        _rv.validate()
        return _rv

# vim: set et sts=4 sw=4 :
