#! /usr/bin/env python
# pylint: disable-msg=R0901,R0904
# R0901: Too many ancestors in all classes derived from Tix widgets
# R0904: ditto, Too many public methods
"""PythonReports Template Designer"""

from code import InteractiveInterpreter
from cStringIO import StringIO
import datetime
import os
from subprocess import Popen
import sys
import traceback

from Tix import *
# override Tix.PanedWindow with Tkinter.PanedWindow
from Tkinter import PanedWindow
from ScrolledText import ScrolledText
from tkColorChooser import askcolor
from tkMessageBox import Message
import tkFileDialog

from PythonReports import datatypes, drivers, version
from PythonReports import template as prt, printout as prp
from PythonReports.builder import Builder
from PythonReports.datatypes import *
from PythonReports.Tk import PreviewWindow
try:
    from PythonReports import pdf
except ImportError:
    pdf = None

NEW_REPORT_TEMPLATE = """<report>
 <font name="body" typeface="Arial" size="8" />
 <layout pagesize="A4" leftmargin="2.5cm" rightmargin="1.5cm"
  topmargin="1.5cm" bottommargin="1.5cm">
  <style font="body" color="0" bgcolor="white" />
  <detail>
   <box height="12" />
  </detail>
 </layout>
</report>
"""

PYTHONREPORTS_URL = "http://pythonreports.sourceforge.net/"
if os.name == "nt":
    URL_HANDLER_COMMAND = "start %s"
else:
    # url_handler.sh is part of urlview package.
    # it's the best way i can think of...
    # perhaps could try /usr/local/bin/netscape, /usr/local/bin/lynx,
    # /usr/local/bin/w3m etc and see which one is executable.
    URL_HANDLER_COMMAND = "/usr/local/bin/url_handler.sh %s"

COPYRIGHT_YEAR = "2006-2012"

### shell

# since we're not interactive, sys does not have ps1 and ps2
try:
    # pylint: disable-msg=E1101,W0104
    # E1101: Module 'sys' has no 'ps1' member - that's what we're trying here
    # W0104: Statement seems to have no effect
    sys.ps1
except AttributeError:
    sys.ps1 = ">>> "
    sys.ps2 = "... "

class Interpreter(InteractiveInterpreter):

    """Python interpreter shell substituting standard streams for code run"""

    def __init__(self, locals, stdin=sys.stdin,
        stdout=sys.stdout, stderr=sys.stderr
    ):
        # pylint: disable-msg=W0622
        # W0622: Redefining built-in 'locals' - the name comes from base class
        InteractiveInterpreter.__init__(self, locals)
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        if "." not in sys.path:
            sys.path.insert(0, ".")

    def runcode(self, code):
        """Execute a code object"""
        # save current standard streams
        _stdin = sys.stdin
        _stdout = sys.stdout
        _stderr = sys.stderr
        # apply redirected streams for the time of running code block
        sys.stdin = self.stdin
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        try:
            # execute the code
            InteractiveInterpreter.runcode(self, code)
        finally:
            # restore saved streams unless changed by the code
            if sys.stdin == self.stdin:
                sys.stdin = _stdin
            if sys.stdout == self.stdout:
                sys.stdout = _stdout
            if sys.stderr == self.stderr:
                sys.stderr = _stderr

class ShellOutputStream(object):

    """File-like objects writing to the text window"""

    def __init__(self, window, tag=""):
        """Initialize the writer

        Parameters:
            window: Tk.Text window
            tag: optional name of the text tag

        """
        super(ShellOutputStream, self).__init__()
        self.window = window
        self.tag = tag

    # writeable file API

    @staticmethod
    def isatty():
        """Return True: the file is connected to a tty-like device"""
        return True

    def write(self, text):
        """Output a text to the window"""
        self.window.insert("end", text, self.tag)
        # window must be refreshed in case we fall into raw_input somewhere
        self.window.see("insert")
        self.window.update_idletasks()

    def writelines(self, iterable):
        """Write a sequence of strings to the window"""
        _write = self.write
        for _line in iterable:
            _write(_line)

class Shell(ScrolledText):

    """Interactive shell widget"""

    # pylint: disable-msg=E0102
    # E0102: redefinition of the Shell class imported from Tix

    @property
    def shell_greeting(self):
        """Interpreter greeting text"""
        return self._("Python %s on %s\n") % (sys.version, sys.platform)

    @property
    def greeting(self):
        """PythonReports greeting text"""
        return self._(
            "Set \"data\" variable to report data sequence for preview.\n")

    def __init__(self, master=None, cnf={}, **kw):
        # pylint: disable-msg=W0102,W0231,W0233
        # W0102: Dangerous default value {} as argument - that's Tk
        # W0231: __init__ method from base class 'ScrolledText' is not called
        # W0233: __init__ method from a non direct base class 'ScrolledText'
        #   is called
        # perhaps pylint got confused by Tk/Tix widget hierarchy?
        ScrolledText.__init__(self, master, cnf=cnf, **kw)
        _toplevel = self.winfo_toplevel()
        self._ = self.gettext = _toplevel.gettext
        self.ngettext = _toplevel.ngettext
        self.locals = {
            "designer": self.winfo_toplevel(),
            "shell": self,
            "data": (),
        }
        self.interpreter = Interpreter(self.locals,
            stdout=ShellOutputStream(self, "output"),
            stderr=ShellOutputStream(self, "error"))
        self.tag_config("prompt", foreground="salmon4")
        self.tag_config("greeting", foreground="salmon4", underline=True)
        self.tag_config("input", underline=True)
        self.tag_config("output", foreground="blue")
        self.tag_config("error", foreground="red")
        # Note: inserting a non-prompt text between shell_greeting
        # (tagged as "prompt") and the first input prompt
        # facilitates input line detection.
        self.insert("insert", self.shell_greeting, "prompt")
        self.insert("insert", self.greeting, "greeting")
        self.prompt()
        self.bind("<Key>", self.OnKeyPress)
        self.bind("<<Paste>>", lambda evt: self.after_idle(self.set_input_tag))

    def OnKeyPress(self, event):
        """Handle window keypress events"""
        # don't process control and navigation keys
        if event.char == "":
            return ""
        # disable text input if not on input line
        if not self.on_input_line():
            return "break"
        # disable backspacing past input area
        if (event.keysym == "BackSpace") \
        and ("input" not in self.tag_names("insert -1c")):
            return "break"
        if (event.keysym == "Return"):
            if self.compare("insert linestart", "!=", "end -1l linestart"):
                # selected a history line - copy to input
                _cmd = self.get(
                    self.tag_nextrange("prompt", "insert linestart")[1],
                    "insert lineend")
                self.delete(
                    self.tag_nextrange("prompt", "end -1l linestart")[1],
                    "end")
                self.insert("end", _cmd, "input")
            self.mark_set("insert", "end")
            self.after_idle(self.execute)
        else:
            # on next idle event, apply input tag
            self.after_idle(self.set_input_tag)
        return ""

    def prompt(self, prompt=sys.ps1):
        """Write new input prompt"""
        # pylint: disable-msg=E1101
        # E1101: Module 'sys' has no 'ps1' member - assigned at toplevel if so
        self.mark_set("insert", "end")
        if self.compare("insert", "!=", "insert linestart"):
            self.insert("insert", "\n")
        self.insert("insert", prompt, "prompt")
        self.see("end")

    def on_input_line(self, index="insert"):
        """Return True if selected line contains input area

        Parameters:
            index: text position on a line to check.

        If the line starts with a standard prompt
        and text position is not in the prompt string,
        return True.  Otherwise return False.

        """
        # pylint: disable-msg=E1101
        # E1101: Module 'sys' has no 'ps1' member - assigned at toplevel if so
        if "input" in self.tag_names(index + " lineend -1c"):
            # the line contains input area
            # FIXME? if there is input text on the line,
            # it is possible to enter new text in and before
            # the prompt area (which won't be executed anyway).
            # On the other hand, this allows to relaunch
            #a history line while input position is in the prompt.
            return True
        if "prompt" not in self.tag_names(index + " linestart"):
            # the line does not start with a prompt - no input possible
            return False
        _prompt_range = self.tag_nextrange("prompt", index + " linestart")
        if self.get(*_prompt_range) not in (sys.ps1, sys.ps2):
            # the line does not start with one of recognized prompts -
            # perhaps a start-up greeting message.
            return False
        if self.compare(index, "<", _prompt_range[1]):
            # input marker is within the prompt
            return False
        # input may follow
        return True

    def set_input_tag(self):
        """Called after a text is added by keyboard: apply "input" tag"""
        if self.on_input_line():
            # current line has input area.
            # apply "input" tag from the end of the prompt
            # to the end of the line
            self.tag_add("input",
                self.tag_nextrange("prompt", "insert linestart")[1],
                "insert lineend")

    def execute(self, line="insert -1l"):
        """Execute selected input line"""
        if self.on_input_line(line):
            _cmd = self.get(
                self.tag_nextrange("prompt", line + " linestart")[1],
                line + " lineend")
            if _cmd == "quit":
                self.winfo_toplevel().destroy()
            else:
                self.interpreter.runsource(_cmd)
                # TODO? continuation lines
                self.prompt()

# widgets for property values

class CodeSelection(ComboBox):

    """Code value selection"""

    def __init__(self, master=None, cnf={}, **kw):
        # pylint: disable-msg=W0102
        # W0102: Dangerous default value {} as argument - that's Tk
        self.values = kw.pop("values", ())
        ComboBox.__init__(self, master=master, cnf=cnf, **kw)
        # we always allow empty value here.
        # tree validation will check for mandatory attributes elsewhere
        if "" not in self.values:
            self.insert("end", "")
        for _val in self.values:
            self.insert("end", _val)
        _designer = self.winfo_toplevel()
        self.entry["background"] = _designer.color_window
        self.entry["disabledbackground"] = _designer.color_window
        self.entry["disabledforeground"] = _designer.color_text
        self.slistbox.listbox["background"] = _designer.color_window
        if len(self.values) > 20:
            _listlen = 20
        else:
            _listlen = 0 # auto
        self.slistbox.listbox["height"] = _listlen

class ColorSelection(Frame):

    """Color value selection"""

    def __init__(self, master=None, cnf={}, **kw):
        # pylint: disable-msg=W0102
        self.var = kw.pop("variable")
        Frame.__init__(self, master=master, cnf=cnf, **kw)
        self["background"] = self.winfo_toplevel().color_panel
        _select = CodeSelection(self, editable=True, variable=self.var,
            values=sorted(Color.names.keys()), validatecmd=self.updateColor)
        _select.grid(row=0, column=0)
        self.indicator = Frame(self, relief=RIDGE, borderwidth=4)
        self.button = Button(self, command=self.OnButton,
            text=self.winfo_toplevel()._("..."))
        self.button.grid(row=0, column=2)
        self.columnconfigure(1, weight=1)
        self.updateColor()

    def updateColor(self, value=NOTHING):
        """Validate the combo box value; update color indicator"""
        _rv = value
        if value is NOTHING:
            _color = Color.fromValue(self.var.get())
        else:
            # got an entered value - must return validated string
            try:
                _color = Color.fromValue(value)
            except InvalidLiteral:
                self.bell()
                # validation will return current value
                _rv = self.var.get()
                _color = Color.fromValue(_rv)
            else:
                self.var.set(value)
        if _color:
            self.indicator["background"] = _color
            self.indicator.grid(row=0, column=1, sticky=NE+SW, padx=5, pady=1)
        else:
            self.indicator.grid_forget()
        return _rv

    def OnButton(self):
        """Run standard color selection dialog"""
        # askcolor returns ((r, g, b), "#rrggbb") or (None, None)
        _color = askcolor(Color.fromValue(self.var.get()))[1]
        if _color:
            self.updateColor(_color)
        self.button.focus_set()

class PropertyEntry(Frame):

    """Generic value entry box"""

    # Entry member of the ComboBox is offset to the right.
    # We need to compensate all other widgets too.
    if os.name == "nt":
        LPAD = 3
    else:
        LPAD = 7

    # This is base class for entries, spin boxes and check boxes.
    # Target widget class is set by this class attribute
    WIDGET = Entry

    # list of (name, value) pairs for default WIDGET initialization keywords
    DEFAULT_OPTIONS = ()

    def __init__(self, master=None, cnf={}, **kw):
        # pylint: disable-msg=W0102
        Frame.__init__(self, master)
        Frame(self, width=self.LPAD).pack(side=LEFT)
        for (_name, _value) in self.DEFAULT_OPTIONS:
            kw.setdefault(_name, _value)
        self.widget = self.WIDGET(master=self, cnf=cnf, **kw)
        self.widget.pack(side=LEFT, fill=BOTH, expand=True)
        self.bind("<FocusIn>", self.OnSetFocus)

    def OnSetFocus(self, event):
        """Automatically pass the focus to the inner widget"""
        self.widget.focus_set()
        self.widget.select_range(0, "end")

class IntegerSelection(PropertyEntry):

    """Spinner box for integer value entry"""

    WIDGET = Control
    DEFAULT_OPTIONS = (("step", 1),)

    if os.name == "nt":
        LPAD = 0
    else:
        LPAD = 5

    def OnSetFocus(self, event):
        """Pass the focus to the entry widget"""
        _entry = self.widget.entry
        _entry.focus_set()
        _entry.select_range(0, "end")

class BooleanSelection(PropertyEntry):

    """Checkbox for boolean value entry"""

    WIDGET = Checkbutton
    DEFAULT_OPTIONS = (
        ("text", ""),
        ("anchor", W),
        ("onvalue", "true"),
        ("offvalue", "false"),
    )

    if os.name == "nt":
        LPAD = 0 # still insufficient

    def __init__(self, master=None, cnf={}, **kw):
        # pylint: disable-msg=W0102
        # When TreeNodeData instantiates PropertyEditors,
        # it passes background color suitable for text entries.
        # This does not look good with check boxes, so remove
        # background color if it is set in the options.
        kw.pop("background", None)
        PropertyEntry.__init__(self, master, cnf, **kw)

    # checkbuttons have no .select_range method
    def OnSetFocus(self, event):
        """Pass the focus to the checkbutton"""
        self.widget.focus_set()

class PropertyEditor(object):

    """Widget factory for an attribute data type"""
    # pylint: disable-msg=R0903
    # R0903: Too few public methods

    # instantiated factories
    FACTORIES = {}

    def __init__(self, widget, varoptname="textvariable", **options):
        """Create a factory

        Parameters:
            widget: Tk widget class
            varoptname: name of the widget option for the value variable
            additional keyword arguments for widget constructor

        """
        super(PropertyEditor, self).__init__()
        self.widget = widget
        self.varoptname = varoptname
        self.options = options

    def __call__(self, variable, *args, **kwargs):
        """Create widget attached to the variable"""
        _options = self.options.copy()
        _options[self.varoptname] = variable
        _options.update(kwargs)
        return self.widget(*args, **_options)

    @classmethod
    def forType(cls, value):
        """Return a widget factory for given value class

        Parameters:
            value: one of the attribute value classes

        """
        try:
            _rv = cls.FACTORIES[value]
        except KeyError:
            assert issubclass(value, datatypes._Value)
            if issubclass(value, datatypes.PenType):
                _rv = cls(CodeSelection, "variable", editable=True,
                    values=value.VALUES + tuple(xrange(5)))
            elif issubclass(value, datatypes._Codes):
                _rv = cls(CodeSelection, "variable", values=value.VALUES)
            elif issubclass(value, Color):
                _rv = cls(ColorSelection, "variable")
            elif issubclass(value, Boolean):
                _rv = cls(BooleanSelection, "variable")
            elif issubclass(value, Integer):
                _rv = cls(IntegerSelection, "variable")
            else:
                _rv = cls(PropertyEntry)
            cls.FACTORIES[value] = _rv
        return _rv

class DataBlockEditor(Frame):

    """PropertyEditor-alike editor for data block contents"""

    # Same As in PropertyEntry
    if os.name == "nt":
        LPAD = 3
    else:
        LPAD = 7

    def __init__(self, data, master=None, cnf={}, **kw):
        """Create editor frame

        Parameters:
            data: editor data object.  must have following properties:
                node: containing TreeNodeData object
                contents: data block contents
                filename: keeps the name of load/save file
                    across instantiations
                filepath: ditto, for default file directory

        """
        # pylint: disable-msg=W0102
        Frame.__init__(self, master, cnf, **kw)
        _toplevel = self.winfo_toplevel()
        self._ = self.gettext = _toplevel.gettext
        self.data = data
        # layout
        Frame(self, width=self.LPAD).pack(side=LEFT)
        _btn_frame = Frame(self)
        _btn_frame.pack(side=TOP)
        self.btn_load = Button(_btn_frame, text=self._("Load File..."),
            command=self.loadFile)
        self.btn_load.pack(side=LEFT, padx=2)
        self.btn_save = Button(_btn_frame, text=self._("Save File..."),
            command=self.saveFile)
        self.btn_save.pack(side=LEFT, padx=2)
        self.text = Text(self, background=_toplevel.color_window)
        self.updateState()
        self.bind("<FocusIn>", lambda event: self.updateState())
        self.bind("<FocusOut>", lambda event: self.textToContents())

    def isBinary(self):
        """Return True if data contents seem to be binary

        If the element has non-empty compression or encoding,
        the data is not editable in the text window.

        WARNING: the caller must ensure that element attributes
        are updated from peer property editors.

        """
        _element = self.data.node.element
        return bool(_element.get("compress") or _element.get("encoding"))

    def textToContents(self):
        """If data is textual, update data contents from the text window"""
        if not self.isBinary():
            # the text widget adds one line feed,
            # but i want to trim all trailing space, even manually entered
            self.data.contents = self.text.get("1.0", "end").rstrip()

    def updateState(self):
        """Set text contents and visibility, disable save if text is empty"""
        self.data.node.updateAttributes()
        _text = self.text
        _binary_data = self.isBinary()
        if _binary_data:
            _text.pack_forget()
        else:
            _text.pack_configure(side=LEFT, fill=X)
            if self.data.contents != _text.get("1.0", "end").rstrip():
                _text.delete("1.0", "end")
                _text.insert("1.0", self.data.contents or "")
                _text.mark_set("insert", "1.0")
                _text.mark_set("sel_first", "1.0")
                _text.mark_set("sel_last", "end")
        # disable save button if data is empty and cannot be entered (binary)
        self.btn_save["state"] = ("disabled", "normal")[not _binary_data
            or bool(self.data.contents)]

    def loadFile(self):
        """Load file contents into the variable"""
        _filename = tkFileDialog.askopenfilename(
            initialfile=self.data.filename,
            initialdir=(self.data.filepath or os.getcwd()),
            filetypes=[(self._("All Files"), "*")])
        if not _filename:
            return
        _binary_data = self.isBinary()
        _file = open(_filename, ("rU", "rb")[_binary_data])
        _contents = _file.read()
        _file.close()
        if not _binary_data:
            # FIXME: encoding should be designer property (probably changeable)
            _contents = _contents.decode("utf-8")
        self.data.contents = _contents
        self.setFileName(_filename)
        self.updateState()

    def saveFile(self):
        """Save variable contents to disk file"""
        _filename = tkFileDialog.asksaveasfilename(
            initialfile=self.data.filename,
            initialdir=(self.data.filepath or os.getcwd()),
            filetypes=[(self._("All Files"), "*")])
        if not _filename:
            return
        if self.isBinary():
            _file_mode = "wb"
            _contents = self.data.contents
        else:
            self.textToContents()
            _file_mode = "wt"
            # FIXME: encoding should be designer property (probably changeable)
            _contents = unicode(self.data.contents).encode("utf-8")
            # add terminating newline for conveninence
            _contents += "\n"
        _file = open(_filename, _file_mode)
        _file.write(_contents)
        _file.close()
        self.setFileName(_filename)

    def setFileName(self, filename):
        """Update default file path after successful load or save"""
        self.data.filename = filename
        self.data.filepath = os.path.dirname(filename)

# data objects

class PropertyData(Structure):

    """Data object representing an attribute editable in the properties list"""
    # pylint: disable-msg=R0903
    # R0903: Too few public methods

class TreeNodeData(list):

    """Data object representing a node of the designer tree"""

    # TODO? for comments and unknown nodes,
    # it is possible to replace the properties list
    # with a Text widget for low-level editing

    # some things cannot be created at the compilation time - root
    # window must be created first.  this class property and
    # following class method do such initialization at the time
    # of the first display operation.  at that time, Tk should
    # be properly initialized yet.
    __do_classinit = True
    @classmethod
    def _classinit(cls, designer):
        """Create classwide structures

        Parameters:
            designer: the Designer object (toplevel window)

        """
        _base_font = designer.option_get("font", Entry)
        if not _base_font:
            _base_font = designer.pl.hlist["font"]
        cls.PROP_NAME_STYLE = designer.tk.call("tixDisplayStyle", TEXT,
            "-justify", RIGHT, "-anchor", E, "-padx", 6, "-pady", 0)
        cls.PROP_NAME_STYLE_MANDATORY = designer.tk.call("tixDisplayStyle",
            TEXT, "-justify", RIGHT, "-anchor", E, "-padx", 6, "-pady", 0,
            "-font", _base_font + " bold underline")
        cls.PROP_VALUE_STYLE = designer.tk.call("tixDisplayStyle", WINDOW,
            "-padx", 0, "-pady", 0)
        cls.__do_classinit = False

    @property
    def treelabel(self):
        """Return text string for the tree entry"""
        return datatypes.element_label(self.element)

    @property
    def path(self):
        """Return dot-separated path for the tree node"""
        if self.parent:
            return ".".join((self.parent.path, self.id))
        else:
            return self.id

    def __init__(self, parent, element, validator, nodeid=None):
        """Initialize the data object

        Parameters:
            parent: parent node data (None for root).
            element: ElementTree object containing node data.
            validator: element validator
            nodeid: optional data identifier (within parent node).
                Default: composed from element tag and object id.

        """
        assert element.tag == validator.tag
        super(TreeNodeData, self).__init__()
        self.element = element
        self.validator = validator
        self.tag = element.tag
        if nodeid is None:
            self.id = "%s@%X" % (self.tag, id(self))
        else:
            self.id = nodeid
        self.parent = parent
        self.canvas_object = None
        self.is_section = element.tag in ("title", "summary",
            "header", "footer", "detail")
        self.is_printable = element.tag in ("field", "line", "rectangle",
            "image", "barcode")
        # create the subtree data
        _collections = [_validator.tag
            for (_validator, _restrict) in validator.children
            if (_restrict not in (_validator.ONE, _validator.ZERO_OR_ONE))]
        _child_validators = validator.child_validators
        for _child in getchildren(element):
            _tag = _child.tag
            # boxes go to element properties -
            # don't create separate tree nodes for them
            if (_tag != "box") and (_tag in _child_validators):
                if _tag in _collections:
                    _id = None # will be computed by child constructor
                else:
                    _id = _tag # there may be only one
                self.append(TreeNodeData(self, nodeid=_id,
                    element=_child, validator=_child_validators[_tag]))
        # attribute edit support
        self.properties = self._build_properties()
        # if this is data element, make a structure for contents editing
        if self.tag == "data":
            try:
                _contents = prt.Data.get_data(self.element)
            except MissingContextError:
                _contents = ""
            self.data = Structure(node=self, contents=_contents,
                filename="", filepath="")
        else:
            self.data = None

    def _build_properties(self):
        """Return a sorted tuple of PropertyData objects

        This is part of the TreeNodeData initialization.

        """
        _properties = []
        for (_name, (_cls, _default)) in self.validator.attributes.iteritems():
            _properties.append(PropertyData(name=_name, type=_cls,
                default=_default, element=self.element, box=False))
        if self.is_printable or self.is_section:
            # we need a box element.  if there's no box, add default one
            _box = self.element.find("box")
            _box_attrs = prt.Box.attributes
            if _box is None:
                _box = SubElement(self.element, "box",
                    attrib=dict((_name, _default)
                        for (_name, (_cls, _default))
                        in _box_attrs.iteritems()))
            if self.is_printable:
                for (_name, (_cls, _default)) in _box_attrs.iteritems():
                    _properties.append(PropertyData(name=_name, type=_cls,
                        default=_default, element=_box, box=True))
            elif self.is_section:
                # add box dimensions but hide box attrs that are not applicable
                for _name in ("x", "y", "width", "height"):
                    (_cls, _default) = _box_attrs[_name]
                    _properties.append(PropertyData(name=_name, type=_cls,
                        default=_default, element=_box, box=True))
        for _prop in _properties:
            # create edit variable
            _prop.var = StringVar()
            _val = _prop.element.get(_prop.name, _prop.default)
            # Note: _val may be REQUIRED for newly added elements
            if _val in (None, REQUIRED):
                _val = u""
            else:
                _val = unicode(_val)
            _prop.var.set(_val)
            # TODO? it is possible to add a write callback to the var
            # and update the element attribute as soon as the value
            # is changed in the editor.
            _prop.widget = PropertyEditor.forType(_prop.type)
            _prop.mandatory = _prop.default is REQUIRED
        _properties.sort(
            key=lambda prop: (prop.box, not prop.mandatory, prop.name))
        return tuple(_properties)

    def addToTree(self, tree, before=None):
        """Create a subtree from this data

        Parameters:
            tree: Tix.Tree widget
            before: optional path of the next sibling.
                If omitted, new node will be added to
                the end of the tree branch.

        """
        if self.__do_classinit:
            self._classinit(tree.winfo_toplevel())
        _kw = {"itemtype": TEXT, "text": self.treelabel}
        if before:
            _kw["before"] = before
        tree.hlist.add(self.path, **_kw)
        for _child in self:
            _child.addToTree(tree)
            tree.hlist.hide_entry(_child.path)

    def loadPropertyList(self, hlist):
        """Put note attributes to Tix.HList for editing"""
        if self.__do_classinit:
            self._classinit(hlist.winfo_toplevel())
        # query current size of the first column and set it to auto
        _col_width = int(hlist.column_width(0))
        _window_color = hlist.winfo_toplevel().color_window
        hlist.column_width(0, "")
        hlist.delete_all()
        for _prop in self.properties:
            _style = (self.PROP_NAME_STYLE, self.PROP_NAME_STYLE_MANDATORY)[
                _prop.mandatory]
            hlist.add(_prop.name, itemtype=TEXT, text=_prop.name,
                style=_style, state=DISABLED)
            _win = _prop.widget(_prop.var, hlist, background=_window_color)
            hlist.item_create(_prop.name, 1, itemtype=WINDOW, window=_win,
                style=self.PROP_VALUE_STYLE)
        # if this is a data element, add nonstandard controls
        if self.data:
            hlist.add("data")
            _win = DataBlockEditor(self.data, hlist)
            hlist.item_create("data", 1, itemtype=WINDOW, window=_win,
                style=self.PROP_VALUE_STYLE)
        # grow the first column if needed
        _col_width = max(_col_width, int(hlist.column_width(0)))
        hlist.column_width(0, _col_width)

    def updateAttributes(self, errors="ignore"):
        """Load element attributes from edit variables

        Parameters:
            errors: error handling scheme: "strict" or "ignore".

        Unlike updateProperties method (defined below),
        updateAttributes sets only attributes of current
        node element and its' box.  It does not touch
        contents for data elements and never descends
        down the tree.

        """
        _element = self.element
        _box = _element.find("box")
        for _prop in self.properties:
            _val = _prop.var.get()
            try:
                _val = _prop.type.fromValue(_val)
            except InvalidLiteral, _err:
                if errors == "strict":
                    raise AttributeConversionError(_prop.name, _val, _err,
                        element=_element, path=self.path)
            if _prop.box:
                # the box must be valid element - created in __init__ if needed
                _box.set(_prop.name, _val)
            else:
                _element.set(_prop.name, _val)

    def updateProperties(self, recursive=False, errors="strict"):
        """Load property values from Tkinter variables

        Parameters:
            recursive: if set, also update children
            errors: error handling scheme: "strict" or "ignore".

        """
        self.updateAttributes()
        if self.data:
            _parent = self.parent.element
            _new = prt.Data.make_element(_parent,
                self.element.attrib, self.data.contents)
            _parent.remove(self.element)
            self.element = _new
        if recursive:
            for _child in self:
                _child.updateProperties(recursive=True, errors=errors)

    def __repr__(self):
        return "<%s@%X: %s>" % (self.__class__.__name__, id(self), self.path)

    def child(self, nodeid):
        """Return child data object for given nodeid"""
        for _child in self:
            if _child.id == nodeid:
                return _child
        else:
            raise KeyError(nodeid)

    def __eq__(self, other):
        # simple comparison to make .index() work
        return self is other

# the application

class Url(Label):

    """Clickable URL widget"""

    DEFAULTS = (
        ("foreground", "blue"),
        ("cursor", "hand2"),
        ("underline", True),
    )

    def __init__(self, master=None, cnf={}, **kw):
        # pylint: disable-msg=W0102
        for (_option, _default) in self.DEFAULTS:
            kw.setdefault(_option, _default)
        Label.__init__(self, master, cnf, **kw)
        self.bind("<Button-1>", self.OnClick)

    def OnClick(self, event):
        """Run URL handler program on the URL"""
        _url = self["text"]
        if _url:
            Popen(URL_HANDLER_COMMAND % _url, shell=True)


class Designer(Toplevel):

    """PythonReports Template Designer"""

    # elements with these tags cannot be added or removed from the tree
    FIXED_TAGS = ("report", "layout", "detail", "box")

    # state properties
    filename = None
    filedir = None
    report = None
    current_node = None
    terminated = False

    @property
    def fileoptions(self):
        """Options for Open/Save File dialogs (dictionary)"""
        return dict(parent=self, defaultextension="prt",
            initialdir=(self.filedir or os.getcwd()),
            initialfile=self.filename,
            filetypes=(
                (self._("PythonReports Templates"), ".prt"),
                (self._("All Files"), "*"),
            ))

    def __init__(self, filename=None, **options):
        """Create the window

        Parameters:
            filename: optional PRT file name to load at start

        """
        Toplevel.__init__(self, class_="PythonReportsDesigner", **options)
        self.build()
        # build a pristine tree to use if filename is not passed
        # or cannot be opened.
        self.makeReport()
        if filename:
            self.loadFile(filename)

    # layout

    def build(self):
        """Do the window layout"""
        self.buildMenu()
        self.statusbar = Label(self, borderwidth=1, relief=SUNKEN)
        self.statusbar.pack(side=BOTTOM, fill=X)
        self.vp = PanedWindow(self, orient="vertical")
        self.vp.pack(fill=BOTH, expand=YES)
        self.hp = PanedWindow(self.vp, orient="horizontal")
        self.tree = Tree(self.hp,
            browsecmd=self.OnTreeBrowse, width=240, height=260)
        _tree_hlist = self.tree.hlist
        _tree_hlist.bind("<Delete>",
            lambda event: self.deleteNode(self.current_node))
        _tree_hlist.bind("<Insert>", self.OnTreeInsert)
        _tree_hlist.bind("<Button-3>", self.OnTreeRClick)
        _tree_hlist.bind("<Shift-F10>", lambda event:
            self.report_menu.tk_popup(*self._get_popup_position()))
        self.hp.add(self.tree)
        # Tkish way to get standard visual attributes is .option_get(),
        # but on X windows that returns empty strings, not suitable
        # for direct use as attribute values.
        # Look at created windows for common appearance.
        # This is quite a weird place to do such initialization,
        # but i want to do this as early as possible.
        self.color_panel = self["background"]
        self.color_text = _tree_hlist["foreground"]
        # FIXME? on X windows, this makes entries slightly darker
        self.color_window = _tree_hlist["background"]
        self.base_font = self.tk.splitlist(_tree_hlist["font"])
        # XXX on X windows, selected item is shown grey on grey!
        if _tree_hlist["selectforeground"] == _tree_hlist["selectbackground"]:
            if _tree_hlist["selectforeground"] == self.color_text:
                # make it inverse
                _tree_hlist["selectforeground"] = self.color_window
            else:
                _tree_hlist["selectforeground"] = self.color_text
        # remaining layout
        self.pl = ScrolledHList(self.hp,
            options="columns 2 background " + self.color_panel)
        self.pl.hlist.bind("<Configure>", self.OnPropListResize)
        self.hp.add(self.pl)
        self.vp.add(self.hp)
        # on windows, the shell gets proportional font.
        # not sure what it will be on other platforms
        # (Gentoo Linux makes it Courier); try Courer
        # FIXME: it is possible to look for monospaced
        # font family names in tkFont.families().
        self.shell = Shell(self.vp, borderwidth=2, relief=SUNKEN,
            width=80, height=20, font=("Courier", self.base_font[1]))
        self.vp.add(self.shell.frame)
        # it was planned to have a drag-and-click-style visual editor
        # on the third pane.  maybe somewhen it'll be implemented too.
        #self.canvas = Canvas(self.vp, borderwidth=2, relief=SUNKEN,
        #    width=720, height=100)
        #self.vp.add(self.canvas)
        self.bind("<Destroy>", self.OnWindowClose)

    def buildAboutDialog(self):
        """Create dialog window for menu command "About..."

        Return value: toplevel widget

        """
        _dlg = Toplevel(self)
        _dlg.title(self._("About PythonReports Designer"))
        _body = Frame(_dlg)
        Label(_body, justify=CENTER, text = self._(
            "PythonReports Designer\n"
            "Version %(version)s  %(date)s\n"
            "Copyright %(year)s alexander smishlajev"
        ) % {
            "version": version.__version__,
            "date": version.__date__.strftime(self._("%d-%b-%Y")),
            "year": COPYRIGHT_YEAR,
        }).pack(side=TOP, padx=10)
        Url(_body, text=PYTHONREPORTS_URL).pack(side=TOP, padx=10)
        _body.pack(side=TOP, padx=10, pady=10)
        (_ul, _text) = self.find_underline(self._("_Ok"))
        _dlg.btn = Button(_dlg, text=_text, underline=_ul,
            command=lambda: _dlg.destroy())
        _dlg.btn.pack(side=BOTTOM, ipadx=10, padx=10, pady=10)
        _dlg.update_idletasks()
        _dlg_x = self.winfo_rootx() \
                + (self.winfo_width() - _dlg.winfo_width()) / 2
        _dlg_y = self.winfo_rooty() \
                + (self.winfo_height() - _dlg.winfo_height()) / 2
        _dlg.geometry("+%i+%i" % (_dlg_x, _dlg_y))
        return _dlg

    def buildMenu(self):
        """Create system menu"""
        _menu = Menu(self, tearoff=False)
        #_menu.pack(side=TOP, fill=X)
        Frame(self, height=2, borderwidth=1, relief=GROOVE).pack(side=TOP,
            fill=X)
        # File menu
        _popup = self._build_menu_item(_menu, ''"_File", item_type="cascade")
        self._build_menu_item(_popup, ''"_New", command=self.OnMenuFileNew)
        self._build_menu_item(_popup, ''"_Open", command=self.OnMenuFileOpen)
        self._build_menu_item(_popup, ''"_Reload",
            command=self.OnMenuFileReload)
        self._build_menu_item(_popup, ''"_Save",
            command=lambda: self.saveFile(self.filename))
        self._build_menu_item(_popup, ''"Save _As...",
            command=lambda: self.saveFile(None))
        _popup.add_separator()
        self._build_menu_item(_popup, ''"E_xit", command=self.OnMenuQuit)
        # Edit menu
        _popup = self._build_menu_item(_menu, ''"_Edit", item_type="cascade")
        self._build_menu_item(_popup, ''"Cu_t", event="<<Cut>>")
        self._build_menu_item(_popup, ''"_Copy", event="<<Copy>>")
        self._build_menu_item(_popup, ''"_Paste", event="<<Paste>>")
        # Report menu
        _popup = self._build_menu_item(_menu, ''"_Report", item_type="cascade")
        self.report_menu = _popup
        self._build_menu_item(_popup, ''"_Insert...", item_type="cascade",
            menu="")
        self._build_menu_item(_popup, ''"_Delete element",
            command=lambda: self.deleteNode(self.current_node))
        self._build_menu_item(_popup, ''"Move _Up", command=self.OnMenuMoveUp)
        self._build_menu_item(_popup, ''"Move Dow_n",
            command=self.OnMenuMoveDown)
        _popup.add_separator()
        self._build_menu_item(_popup, ''"Print Pre_view", command=self.preview)
        self._build_menu_item(_popup, ''"_Write Printout...",
            command=self.printout)
        # Help menu
        _popup = self._build_menu_item(_menu, ''"_Help", item_type="cascade")
        self._build_menu_item(_popup, ''"_About...", command=self.OnMenuAbout)
        # set window menu to created tree
        self["menu"] = _menu
        # create insertion menus and validator data
        self.element_validators = {}
        self.insert_menus = {}
        self.buildInsertionMenus(prt.Report)

    def buildInsertionMenus(self, validator):
        """Create a set of menus and validator data for element insertion"""
        _tag = validator.tag
        # return early if menu is already present (break recursion on group,
        # may be used to make some menus in different way)
        if _tag in self.insert_menus:
            return
        _menu = self.insert_menus[_tag] = []
        # return early if validator has no children (insert menu empty/unused)
        if not validator.children:
            return
        # create submenu for "insert element" cascade
        _hotkeys = set()
        for (_child, _restrict) in validator.children:
            self.element_validators[(_tag, _child.tag)] = (_child, _restrict)
            self.buildInsertionMenus(_child)
            # FIXED_TAGS cannot be inserted
            if _child.tag not in self.FIXED_TAGS:
                # find the first letter of the element tag
                # not used as a hot key yet
                for (_underline, _letter) in enumerate(_child.tag):
                    if _letter not in _hotkeys:
                        _hotkeys.add(_letter)
                        break
                else:
                    _underline = -1
                # pylint: disable-msg=W0631
                # W0631: Using possibly undefined loop variable _underline
                #   if the loop is empty, the variable is initialized
                #   in the else clause.
                _menu.append(dict(label=_child.tag, underline=_underline,
                    command=lambda tag=_child.tag: self.insertNode(tag)))

    @staticmethod
    def find_underline(label):
        """Return (underline, text) for given label"""
        _underline = label.find("_")
        if _underline >= 0:
            _text = label[:_underline] + label[_underline+1:]
        else:
            _text = label
        return (_underline, _text)

    def _build_menu_item(self, parent, label, item_type="command",
            event=None, **options
    ):
        """Create menu button with popup menu

        Parameters:
            parent: containing menu widget.
            label: button label (subject for gettext translation).
                Underscore character in label text means next character
                will be underlined.  If the label contains more than
                one underscore character, second and following
                underscores are displayed.
            item_type: item type - "command", "cascade" etc.
                Default: "command".
            event: optional name of virtual event to post
                when menu command is selected (overrides "command"
                procedure set in options, if any).
            additional keyword arguments will be passed right to Tk.

        If item_type is "cascade", return associated submenu widget.
        Otherwise return None.

        """
        (_underline, _text) = self.find_underline(self._(label))
        if _underline >= 0:
            options.setdefault("underline", _underline)
        if event:
            options["command"] = lambda evt=event: self._post_event(evt)
        try:
            _make = getattr(parent, "add_" + item_type)
        except AttributeError:
            raise ValueError("Unsupported menu object type: %s" % item_type)
        if item_type == "cascade":
            # create submenu unless passed in options
            if "menu" not in options:
                options["menu"] = Menu(parent, tearoff=False)
            _rv = options["menu"]
        else:
            _rv = None
        _make(label=_text, **options)
        return _rv

    # event handlers

    def _post_event(self, event):
        """Send a virtual event to widget having focus"""
        _widget = self.focus_get()
        if _widget:
            _widget.event_generate(event)

    def OnWindowClose(self, event):
        """Handle Destroy event for the toplevel window"""
        # this handler gets destroy events for all child widgets,
        # including Message dialogs.  Check update when the first
        # child of the tree widget gets destroyed, ignore all others.
        if not self.terminated \
        and str(event.widget).startswith(str(self.tree)):
            # some of the window widgets have been destroyed yet
            # and the window looks weird.  hide it away.
            # (we cannot return to the editor anyway.)
            self.withdraw()
            self.checkUpdate(dlgtype="yesno")
            self.terminated = True

    def OnMenuFileNew(self):
        """Create new empty template"""
        if not self.checkUpdate():
            return
        self.makeReport()

    def OnMenuFileOpen(self):
        """Load template file"""
        if not self.checkUpdate():
            return
        _filename = tkFileDialog.askopenfilename(**self.fileoptions)
        if _filename:
            self.loadFile(_filename)

    def OnMenuFileReload(self):
        """Re-read currently loaded template file"""
        if (self.filename and self.checkUpdate()):
            self.loadFile(self.filename)

    def OnMenuQuit(self):
        """Exit the application"""
        if not self.checkUpdate():
            return
        self.destroy()

    def OnMenuAbout(self):
        """Display "About..." dialog"""
        _focus = self.focus_get() or self.tree.hlist
        _dlg = self.buildAboutDialog()
        _dlg.btn.focus_set()
        _dlg.grab_set()
        self.wait_window(_dlg)
        _focus.focus_set()

    def OnMenuMoveUp(self):
        """Move selected node before it's previous sibling"""
        _path = self.current_node
        _data = self.getNodeData(_path)
        _parent = _data.parent
        if not _parent:
            # can't happen - menu item should be disabled
            return
        _idx = _parent.index(_data)
        if _idx < 1:
            # can't happen either
            return
        _sibling = _parent[_idx - 1]
        _parent[_idx-1:_idx+1] = (_data, _sibling)
        self.tree.hlist.delete_entry(_path)
        _data.addToTree(self.tree, before=_sibling.path)
        self.tree.autosetmode()
        self.select(_path)

    def OnMenuMoveDown(self):
        """Move selected node after it's next sibling"""
        _path = self.current_node
        _data = self.getNodeData(_path)
        _parent = _data.parent
        if not _parent:
            # can't happen - menu item should be disabled
            return
        _idx = _parent.index(_data)
        if (_idx + 1) >= len(_parent):
            # can't happen either
            return
        _parent[_idx:_idx+2] = (_parent[_idx+1], _data)
        self.tree.hlist.delete_entry(_path)
        try:
            _before = _parent[_idx+2]
        except IndexError:
            # at the end of the siblings list
            _before = None
        else:
            _before = _before.path
        _data.addToTree(self.tree, before=_before)
        self.tree.autosetmode()
        self.select(_path)

    @staticmethod
    def _enabled(enable):
        """Return Tk widget state constant for boolean value"""
        return (DISABLED, NORMAL)[bool(enable)]

    def OnTreeBrowse(self, node, force=False):
        """Select new item on the tree"""
        # XXX why the browse event always comes twice?
        if (node == self.current_node) and not force:
            return
        # spare some keystrokes and attribute lookups
        _rmenu = self.report_menu
        # TODO? if self.current_node is not None,
        # update from the properties list
        _data = self.getNodeData(node)
        _data.loadPropertyList(self.pl.hlist)
        if (not self.current_node) \
        or (_data.tag != self.getNodeData(self.current_node).tag):
            # element type changed - replace insertion menu
            # destroy current menu, if any
            _imenu = _rmenu.entrycget(0, "menu")
            if _imenu:
                _imenu = _rmenu.nametowidget(_imenu)
                _rmenu.entryconfigure(0, state=DISABLED, menu="")
                _imenu.destroy()
            # build new insertion menu, if any
            _imenu_def = self.insert_menus[_data.tag]
            if _imenu_def:
                _imenu = Menu(_rmenu, tearoff=False)
                for _args in _imenu_def:
                    self._build_menu_item(_imenu, **_args)
                _rmenu.entryconfigure(0, state=NORMAL, menu=_imenu)
        self.current_node = node
        # enable/disable other element commands
        _rmenu.entryconfigure(1,
            state=self._enabled(_data.tag not in self.FIXED_TAGS))
        if _data.parent is None:
            _rmenu.entryconfigure(2, state=DISABLED)
            _rmenu.entryconfigure(3, state=DISABLED)
        else:
            _index = _data.parent.index(_data)
            _rmenu.entryconfigure(2, state=self._enabled(_index > 0))
            _rmenu.entryconfigure(3,
                state=self._enabled((_index + 1) < len(_data.parent)))

    def _get_popup_position(self):
        """Return position for the tree popup menu

        Menu is popped up with it's top left corner just below
        currently selected tree node, offset from the left side
        by the nesting level.

        Return value: 2-element tuple (x, y).

        """
        _hlist = self.tree.hlist
        _bbox = _hlist.tk.call(str(_hlist), "info", "bbox", self.current_node)
        _ypos = _hlist.winfo_rooty() + int(self.tk.splitlist(_bbox)[3])
        _xpos = _hlist.winfo_rootx() + 20 * (self.current_node.count(".") + 1)
        return (_xpos, _ypos)

    def OnTreeRClick(self, event):
        """Right click on the tree list - open pulldown menu"""
        # set focus to the tree: click moves selection pointer
        # and it looks like the pointer can further be moved
        # by keyboard.  not true unless we force focus to the tree.
        _hlist = self.tree.hlist
        _hlist.focus_set()
        # select tree node nearest to the click position
        _path = _hlist.nearest(event.y)
        self.select(_path)
        # menu will be popped up below selected row,
        # horizontally near to the click position
        self.report_menu.tk_popup(event.x_root, self._get_popup_position()[1])

    def OnTreeInsert(self, event):
        """Insert key pressed in the tree - pop up insert element menu"""
        _menu = self.report_menu.entrycget(0, "menu")
        if _menu:
            self.nametowidget(_menu).tk_popup(*self._get_popup_position())

    def OnPropListResize(self, event=0):
        """Adjust width of value col in the property list upon window resize"""
        _hlist = self.pl.hlist
        _hlist.column_width(1, max(100,
            _hlist.winfo_width() - int(_hlist.column_width(0))))

    # i18n stub
    # these methods are noop because we do not have message catalogs yet

    @staticmethod
    def gettext(msg):
        """Return msg translated to selected language"""
        return msg

    _ = gettext

    @staticmethod
    def ngettext(singular, plural, n):
        """Translate a message with plural forms lookup"""
        # pylint: disable-msg=C0103
        # C0103: Invalid name "n" - I quite agree.
        if n == 1:
            return singular
        else:
            return plural

    # data processing

    def updateTitle(self):
        """Change window title when self.filename changes"""
        if self.filename:
            _title = self._("%s - PythonReports Designer") \
                % os.path.basename(self.filename)
        else:
            _title = self._("PythonReports Designer")
        self.title(_title)

    def select(self, path):
        """Select a node on the tree

        Parameters:
            path: path for the node to select.

        """
        _hlist = self.tree.hlist
        _hlist.see(path)
        _hlist.selection_clear()
        _hlist.selection_set(path)
        _hlist.anchor_set(path)
        self.OnTreeBrowse(path, force=True)

    def getNodeData(self, path):
        """Return tree node data for given path"""
        assert (path == "report") or path.startswith("report.")
        _data = self.data
        for _nodeid in path.split(".")[1:]:
            _data = _data.child(_nodeid)
        return _data

    def deleteNode(self, path):
        """Delete an element of the tree

        Parameters:
            path: path for the node to delete.

        """
        _data = self.getNodeData(path)
        if _data.tag in self.FIXED_TAGS:
            # cannot delete
            return
        if path == self.current_node:
            self.current_node = None
        _parent = _data.parent
        _index = _parent.index(_data)
        _element_index = getchildren(_parent.element).index(_data.element)
        _hlist = self.tree.hlist
        if _data.tag == "group":
            # find contained group or detail element -
            # will replace deleted group
            for _child in _data:
                if _child.tag in ("group", "detail"):
                    _replace = _child
                    break
            else:
                # this could not happen because the tree is verified on load
                # and we do not allow to remove the detail element.
                raise RuntimeError("No 'group' or 'detail' child found.")
            _replace.parent = _parent
            _parent[_index] = _replace
            _parent.element[_element_index] = _replace.element
            _hlist.delete_entry(path)
            _replace.addToTree(self.tree)
            self.tree.autosetmode()
            self.select(_replace.path)
        else:
            _hlist.delete_entry(path)
            del _parent[_index], _parent.element[_element_index]
            if _index < len(_parent):
                _select = _parent[_index]
            elif _index > 0:
                _select = _parent[_index - 1]
            else:
                _select = _parent
                # deleted last child - remove open/close indicator
                self.tree.setmode(_parent.path, "none")
            self.select(_select.path)

    @staticmethod
    def _create_template_element(parent, validator):
        """Element creation helper: make subelement and all required children
        """
        _element = SubElement(parent, validator.tag)
        for (_child, _restrict) in validator.children:
            if _restrict in (validator.ONE, validator.ONE_OR_MORE):
                # pylint: disable-msg=W0212
                # W0212: Access to a protected member _create_template_element
                #   of a client class - it's not a client, it's this own class.
                Designer._create_template_element(_element, _child)
        return _element

    def insertNode(self, tag, before=sys.maxint):
        """Insert a child element at currently selected node

        Parameters:
            tag: element tag for new element
            before: optional element index (zero-based).
                If passed, new element will be added before
                the element at this index.  If omitted, new
                element will be added to the end.
                Ignored if the tag is "group".

        """
        _node = self.getNodeData(self.current_node)
        (_validator, _restrict) = self.element_validators[(_node.tag, tag)]
        if tag == "group":
            _nodeid = tag
            # "before" is unreliable in this case
            # because we are deleting the inner element
            # (group or detail) from the siblings list
            # and "before" position may shift up or down.
            # force append to the end of list.
            # pylint: disable-msg=C0103
            # C0103: Invalid name "before"
            before = sys.maxint
            # find contained group or detail element -
            # will replace deleted group
            for _child in _node:
                if _child.tag in ("group", "detail"):
                    _inner = _child
                    break
            else:
                raise RuntimeError("No 'group' or 'detail' child found.")
        elif _restrict in (_validator.ONE, _validator.ZERO_OR_ONE):
            # there may be only one child with this tag
            for _child in _node:
                if _child.tag == tag:
                    return
            # single items have nodeids set to tag for aesthetics
            _nodeid = tag
        else:
            # collections compute nodeid in child constructor
            _nodeid = None
        # FIXME: _create_template_element lacks "before" argument.
        #       NodeData/Element sequences may get out of sync.
        _element = self._create_template_element(_node.element, _validator)
        _child = TreeNodeData(_node, nodeid=_nodeid, element=_element,
            validator=_validator)
        _node.insert(before, _child)
        if tag == "group":
            self.tree.hlist.delete_entry(_inner.path)
            _node.remove(_inner)
            _node.element.remove(_inner.element)
            _child.append(_inner)
            _element.append(_inner.element)
            _inner.parent = _child
        self.tree.open(_node.path)
        if before < (len(_node) - 1):
            _child.addToTree(self.tree, before=_node[before + 1].path)
        else:
            _child.addToTree(self.tree)
        self.tree.autosetmode()
        self.select(_child.path)

    def loadTreeContents(self):
        """Change the tree contents when new report template is loaded"""
        _tree = self.tree
        _tree.hlist.delete_all()
        self.data = TreeNodeData(None, nodeid="report",
            element=self.report.getroot(), validator=prt.Report)
        self.data.addToTree(_tree)
        _tree.autosetmode()
        _tree.open("report")
        self.select("report")
        # Note: str(report) returns normalized text,
        # may differ from contents of the loaded file.
        # Note: loaded_text must be evaluated
        # after TreeNodeData construction (that may
        # make some unsignificant changes to the tree)
        self.loaded_text = str(self.report)

    def loadFile(self, filename):
        """Load report file"""
        # pylint: disable-msg=W0703
        # W0703: Catch "Exception" - yep, that's what we do here
        try:
            self.report = prt.load(filename)
        except Exception, _err:
            traceback.print_exc()
            _focus = self.focus_get() or self.tree.hlist
            Message(self, icon="error", type="ok",
                title=self._("File load error"),
                message=self._("Error loading file %(file)s:\n%(error)s") % {
                    "file": os.path.abspath(filename),
                    "error": str(_err) or _err.__class__.__name__,
                }).show()
            # FIXME: still unfocused...
            _focus.focus_set()
            return
        self.filename = filename
        self.filedir = os.path.dirname(os.path.abspath(filename))
        self.updateTitle()
        self.select("report")
        self.loadTreeContents()

    def makeReport(self):
        """Create an empty report tree"""
        self.report = prt.load(StringIO(NEW_REPORT_TEMPLATE))
        self.filename = None
        self.updateTitle()
        self.current_node = None
        self.loadTreeContents()

    def saveFile(self, filename):
        """Save report template file

        Parameters:
            filename: destination filename.
                if None, open Save File dialog.

        Return value: True if the template saved successfully,
            False otherwise.

        """
        if not self.updateTree():
            return False
        if not filename:
            # pylint: disable-msg=C0103
            # C0103: Invalid name "filename"
            filename = tkFileDialog.asksaveasfilename(**self.fileoptions)
            if not filename:
                return False
        self.report.write(filename)
        self.report.filename = self.filename = filename
        self.filedir = os.path.dirname(os.path.abspath(filename))
        self.loaded_text = str(self.report)
        self.updateTitle()
        return True

    def updateTree(self, errors="strict"):
        """Update template tree from editing buffers

        Parameters:
            errors: error handling scheme: "strict" or "ignore".
                If "strict", validation is performed for the
                template structure.  If "ignore", attributes
                with invalid values set in property editors
                will remain unchanged.

        Return value: False if validation failed, True otherwise.

        """
        try:
            self.data.updateProperties(recursive=True, errors=errors)
        except AttributeConversionError, _err:
            self.select(_err.path)
            self.update_idletasks()
            Message(self, icon="error", type="ok",
                title=self._("Invalid Value"), message=self._(
                    "Value %(value)r is not valid for attribute \"%(name)s\"\n"
                    "(value must be of type %(class)s).") % {
                        "value": _err.value,
                        "name": _err.attribute,
                        "class": self._(_err.exception.datatype.__name__)
                    }
            ).show()
            self.nametowidget(self.pl.hlist.item_cget(_err.attribute, 1,
                "-window")).focus_set()
            return False
        if errors == "strict":
            try:
                self._validate(self.report, prt.Report)
            except XmlValidationError, _err:
                # TODO: make translated messages
                # for different validation errors
                # TODO: select tree element that raised the error
                # (_err contains node path in XPath notation)
                Message(self, icon="error", type="ok",
                    title=self._("Validation Error"), message=self._(
                        "The template contains following error:\n%s"
                    ) % _err
                ).show()
                self.tree.hlist.focus_set()
                return False
        return True

    def checkUpdate(self, dlgtype="yesnocancel"):
        """Check if the template has unsaved changes; prompt to save

        Parameters:
            dlgtype: MessageBox type - "yesno" or "yesnocancel".

        If there are unsaved changes in the tree, prompt user
        to save the template.  By default, the prompt dialog
        has buttons "Yes", "No" and "Cancel".  When the window
        is closed by operational system, the operation cannot
        be canceled, so there may be only "Yes" and "No" buttons,
        giving the user one last chance to save changes.

        Return value: False to cancel operation, True to proceed.

        """
        # first, do silent update (saveFile will do validating update later)
        self.updateTree(errors="ignore")
        if str(self.report) == self.loaded_text:
            # no changes
            return True
        _focus = self.focus_get()
        if self.filename:
            _msg = self._("Do you want to save the changes you made to %s?") \
                % os.path.basename(self.filename)
        else:
            _msg = self._("Do you want to save the changes"
                " you made to new template?")
        _okcancel = Message(self, icon="warning", type=dlgtype,
            title=self._("Unsaved changes detected"), message=_msg).show()
        _focus.focus_set()
        if _okcancel == "cancel":
            return False
        elif _okcancel == "no":
            return True
        return self.saveFile(self.filename)

    @staticmethod
    def _validate(tree, validator):
        """Run Template/Printout validator on an ElementTree"""
        _root = tree.getroot()
        validator(tree, _root, "/" + _root.tag)

    def _get_report_data(self):
        """Return data sequence for report preview or output

        If the report cannot be run, return None

        """
        if not self.updateTree():
            return None
        # message boxes take focus away.  remember currently focused widget
        # to regain the focus after message display.
        _focus = self.focus_get()
        # validate the tree
        # XXX seems to be a repetition (done in updateTree?) - unneeded
        self._validate(self.report, prt.Report)
        # get the data
        try:
            _data = self.shell.locals["data"]
        except KeyError:
            _msg = Message(self, icon="error", type="okcancel",
                title=self._("Missing Report data"),
                message=self._("Report data sequence is not defined.\n"
                    "Please set \"data\" variable in the shell.\n\n"
                    "Press <Ok> to run the report with empty sequence\n"
                    "or <Cancel> to return to designer window."),
                )
            if _msg.show() != "ok":
                _focus.focus_set()
                return None
            _data = ()
        else:
            if not _data:
                _msg = Message(self, icon="warning", type="okcancel",
                    title=self._("Missing Report data"),
                    message=self._("Report data sequence is empty.\n\n"
                        "Run the report anyway?"),
                    )
                if _msg.show() != "ok":
                    Message(self, icon="info", type="ok",
                        title=self._("Hint"), message=self._(
                            "Please set \"data\" variable in the shell"
                        )).show()
                    _focus.focus_set()
                    return None
                _data = ()
        _focus.focus_set()
        return _data

    def _run_preview(self):
        """Build and show the report"""
        _data = self._get_report_data()
        if _data is None:
            return
        # build printout tree
        # Note: it is best to use same backend for both building and rendering.
        # since we'll surely use Tk renderer, use Tk backend for builder too.
        _printout = Builder(self.report, text_backend="Tk").run(_data)
        # printout must be validated before it can be displayed
        self._validate(_printout, prp.Printout)
        # open preview
        if self.filename:
            _title = self._("%s - Report Preview") \
                % os.path.basename(self.filename)
        else:
            _title = self._("Report Preview")
        _preview = PreviewWindow(master=self, report=_printout, title=_title)
        _preview.geometry("%ix%i" % (self.winfo_width(), self.winfo_height()))
        _preview.focus_set()

    def preview(self):
        """Show Report Preview for current template"""
        # pylint: disable-msg=W0703
        # W0703: Catch "Exception" - yep, that's what we do here
        _focus = self.focus_get() or self.tree.hlist
        try:
            try:
                self["cursor"] = "watch"
                self._run_preview()
            finally:
                self["cursor"] = ""
        except Exception, _err:
            traceback.print_exc()
            Message(self, icon="error", type="ok",
                title=self._("Report preview error"),
                message=self._("Error running report preview:\n%s")
                % (str(_err) or _err.__class__.__name__)).show()
            _focus.focus_set()

    def printout(self):
        """Build and save report printout"""
        _data = self._get_report_data()
        if _data is None:
            return
        if self.filename:
            _filename = os.path.splitext(self.filename)[0]
        else:
            _filename = ""
        _filetypes = [
            (self._("PythonReports Printouts"), ".prp"),
            (self._("All Files"), "*"),
        ]
        if pdf:
            _filetypes.insert(1, (self._("Adobe PDF Files"), ".pdf"))
        _filename = tkFileDialog.asksaveasfilename(
            initialfile=_filename, initialdir=(self.filedir or os.getcwd()),
            filetypes=_filetypes, defaultextension=".prp")
        if not _filename:
            return
        _printout = Builder(self.report).run(_data)
        # printout must be validated before it can be saved
        self._validate(_printout, prp.Printout)
        # take output type from file extension
        if pdf and _filename.lower().endswith(".pdf"):
            pdf.write(_printout, _filename)
        else:
            _printout.write(_filename)

def run(argv=sys.argv):
    """Command line executable"""
    if len(argv) > 2:
        print "Usage: %s [template]" % argv[0]
        sys.exit(2)
    _root = Tk()
    _root.withdraw()
    _win = Designer(*argv[1:])
    _root.wait_window(_win)

if __name__ == "__main__":
    run()

# vim: set et sts=4 sw=4 :
