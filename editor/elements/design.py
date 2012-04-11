"""Visual design elements, that can be placed in section"""
"""
11-apr-2012 [kacah]    Subreport moved to section.py, added EventsHandler,
                       added DesignPlace, added Field
03-apr-2012 [kacah]    created, added Subreport

"""
import PythonReports.template as te
import wx
import wx.lib.ogl as wxogl

from elements.element import Element
import environment as env
import utils


MIN_SIZE = 10

class DesignPlace(wxogl.ShapeCanvas):
    """Place for painting visual elements"""

    def __init__(self, parent, width):
        wxogl.ShapeCanvas.__init__(self, parent, size=(width, MIN_SIZE))

        self.SetMinSize((width, MIN_SIZE))
        self.SetMaxSize((width, -1))

        self.diagram = wxogl.Diagram()
        self.SetDiagram(self.diagram)
        self.diagram.SetCanvas(self)

        self.elements = []

    def set_width(self, width):
        """Set min, max and actual width of design place"""

        self.SetSize((width, self.GetSize().GetHeight()))
        self.SetMinSize((width, MIN_SIZE))
        self.SetMaxSize((width, -1))

    def OnLeftClick(self, x, y, keys):
        """Create new elements if needed"""
        env.remove_focus()

        _tool = env.get_active_editing_tool()

        if _tool == env.EditingTools.field:
            self.add_element(Field(self, x, y))

    def add_element(self, _element):
        """Add new element to this DesignPlace"""

        self.elements.append(_element)
        env.OnPropertyListener(_element)
        self.Refresh(False)


class AllShapesEvtHandler(wxogl.ShapeEvtHandler):
    """Listener for all shapes' events. All methods are overrided"""

    def __init__(self):
        wxogl.ShapeEvtHandler.__init__(self)

    def OnLeftClick(self, x, y, keys=0, attach=0):
        shape = self.GetShape()

        if shape.Selected():
            env.remove_focus()
        else:
            env.OnPropertyListener(shape)

    def OnBeginDragLeft(self, x, y, keys, attach):
        env.toggle_double_buffering(False)

        self.GetPreviousHandler().OnBeginDragLeft(x, y, keys, attach)

        shape = self.GetShape()
        if not shape.Selected():
            self.OnLeftClick(x, y, keys, attach)

    def OnEndDragLeft(self, x, y, keys=0, attach=0):
        self.GetPreviousHandler().OnEndDragLeft(x, y, keys, attach)

        env.toggle_double_buffering(True)

    def OnSizingBeginDragLeft(self, pt, x, y, keys, attach):
        env.toggle_double_buffering(False)

        self.GetPreviousHandler().OnSizingBeginDragLeft(pt, x, y, keys, attach)

    def OnSizingEndDragLeft(self, pt, x, y, keys, attach):
        self.GetPreviousHandler().OnSizingEndDragLeft(pt, x, y, keys, attach)

        env.toggle_double_buffering(True)

    def OnMovePost(self, dc, x, y, oldX, oldY, display):
        self.GetPreviousHandler().OnMovePost(dc, x, y, oldX, oldY, display)

        #fix bug on MacOS
        if "wxMac" in wx.PlatformInfo:
            shape = self.GetShape()
            shape.GetCanvas().Refresh(False)


BOX_ONE = [te.Box]
DATA_ZERO_OR_ONE = [te.Data]
STYLE_UNRESTRICTED = [te.Style]

DEFAULT_WIDTH = 100
DEFAULT_HEIGHT = 40

class ShapeBase(object):
    """Methods for all shapes"""

    def init_shape(self, parent_canvas, x, y):
        """Setup settings for shape"""

        self.SetDraggable(True, True)
        self.SetCanvas(parent_canvas)
        self.set_pos(x, y)
        self.SetPen(wx.BLACK_PEN)
        self.SetBrush(wx.LIGHT_GREY_BRUSH)
        self.SetCentreResize(False)
        parent_canvas.diagram.AddShape(self)
        self.Show(True)

        _evthandler = AllShapesEvtHandler()
        _evthandler.SetShape(self)
        _evthandler.SetPreviousHandler(self.GetEventHandler())
        self.SetEventHandler(_evthandler)

    def highlight(self, need_hl):
        """Highlight shape"""

        _canvas = self.GetCanvas()
        _dc = wx.ClientDC(_canvas)
        _canvas.PrepareDC(_dc)

        self.Select(need_hl, _dc)

    def set_pos(self, x, y):
        """Set position of shape. Count it correcting center"""

        _size = self.GetBoundingBoxMin()
        x = x + _size[0] / 2
        y = y + _size[1] / 2
        self.SetX(x)
        self.SetY(y)


FIELD_MAIN = te.Field

class Field(ShapeBase, wxogl.TextShape, Element):
    """Visual field element"""

    def __init__(self, parent_canvas, x, y):
        wxogl.TextShape.__init__(self, DEFAULT_WIDTH, DEFAULT_HEIGHT)
        Element.__init__(self, FIELD_MAIN, DATA_ZERO_OR_ONE, BOX_ONE,
            STYLE_UNRESTRICTED)

        self.init_shape(parent_canvas, x, y)
        self.set_text("sdfsdf")

    def set_text(self, text):
        """Set text of field"""

        self.ClearText()
        self.AddText(text)
