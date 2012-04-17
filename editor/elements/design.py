"""Visual design elements, that can be placed in section"""
"""
13-apr-2012 [kacah]    Added Line, Rectangle, Image, Barcode
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

        self.active = None
        self.init_lists()

    def init_lists(self):
        """Setup lists for all types of elements"""

        self.elements = {}
        self.elements[Field] = []
        self.elements[Rectangle] = []
        self.elements[Image] = []
        self.elements[Barcode] = []
        self.elements[Line] = []

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

        elif _tool == env.EditingTools.rect:
            self.add_element(Rectangle(self, x, y))

        elif _tool == env.EditingTools.image:
            self.add_element(Image(self, x, y))

        elif _tool == env.EditingTools.barcode:
            self.add_element(Barcode(self, x, y))

        elif _tool == env.EditingTools.line:
            self.add_element(Line(self, x, y))

    def add_element(self, _element):
        """Add new element to this DesignPlace"""

        self.elements[_element.__class__].append(_element)
        env.OnPropertyListener(_element)
        self.Refresh(False)

    def delete_active(self):
        """Delete active element from DesignPlace"""

        if self.active:
            _elem_to_delete = self.active
            env.remove_focus()
            self.elements[_elem_to_delete.__class__].remove(_elem_to_delete)
            self.RemoveShape(_elem_to_delete)
            self.Refresh(False)

    def force_data_update(self):
        """Update all elements that are linked to report data"""

        for _field in self.elements[Field]:
            _field.update_text()


class AllShapesEvtHandler(wxogl.ShapeEvtHandler):
    """Listener for all shapes' events. All methods are overrided"""

    def __init__(self):
        wxogl.ShapeEvtHandler.__init__(self)

    def OnLeftClick(self, x, y, keys=0, attach=0):
        shape = self.GetShape()
        env.OnPropertyListener(shape)

    def OnBeginDragLeft(self, x, y, keys, attach):
        env.toggle_double_buffering(False)

        self.GetPreviousHandler().OnBeginDragLeft(x, y, keys, attach)

        shape = self.GetShape()
        if not shape.Selected():
            self.OnLeftClick(x, y, keys, attach)

    def OnEndDragLeft(self, x, y, keys=0, attach=0):
        self.GetPreviousHandler().OnEndDragLeft(x, y, keys, attach)

        self.GetShape().synchronize_box()
        env.toggle_double_buffering(True)

    def OnSizingBeginDragLeft(self, pt, x, y, keys, attach):
        env.toggle_double_buffering(False)

        self.GetPreviousHandler().OnSizingBeginDragLeft(pt, x, y, keys, attach)

    def OnSizingEndDragLeft(self, pt, x, y, keys, attach):
        self.GetPreviousHandler().OnSizingEndDragLeft(pt, x, y, keys, attach)

        self.GetShape().synchronize_box()
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

class ShapeBase(Element):
    """Methods for all shapes"""

    def __init__(self, main_val, zero_or_one_val):
        Element.__init__(self, main_val, zero_or_one_val, BOX_ONE,
            STYLE_UNRESTRICTED)

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

        self.synchronize_box()

    def highlight(self, need_hl):
        """Highlight shape"""

        _canvas = self.GetCanvas()
        _dc = wx.ClientDC(_canvas)
        _canvas.PrepareDC(_dc)

        if need_hl:
            _canvas.active = self
        else:
            _canvas.active = None
        self.Select(need_hl, _dc)

    def get_shape_center(self):
        """Return local shape center"""

        return (self.GetWidth() / 2, self.GetHeight() / 2)

    def set_pos(self, x, y):
        """Set position of shape according left top corner"""

        (_center_x, _center_y) = self.get_shape_center()
        self.SetX(x + _center_x)
        self.SetY(y + _center_y)

    def get_pos(self):
        """Get position (x, y) of left top corner"""

        (_center_x, _center_y) = self.get_shape_center()
        return (self.GetX() - _center_x, self.GetY() - _center_y)

    def get_size(self):
        """Get size tuple from properties"""
        return (self.GetWidth(), self.GetHeight())

    def correct_x_dimension(self, dim):
        """If dim < 0 make it as offset from from width"""

        if dim < 0:
            _size = self.GetCanvas().GetSize()
            dim = _size.GetWidth() + dim
        return dim

    def correct_y_dimension(self, dim):
        """If dim < 0 make it as offset from from height"""

        if dim < 0:
            _size = self.GetCanvas().GetSize()
            dim = _size.GetHeight() + dim
        return dim

    def get_precise_rectangle(self):
        """Get bounding box of line from properties - more precise than shapes"""

        _x = utils.dim_to_screen(self.get_value("box", "x"))
        _y = utils.dim_to_screen(self.get_value("box", "y"))
        _width = utils.dim_to_screen(self.get_value("box", "width"))
        _height = utils.dim_to_screen(self.get_value("box", "height"))

        _x = self.correct_x_dimension(_x)
        _y = self.correct_y_dimension(_y)
        _width = self.correct_x_dimension(_width)
        _height = self.correct_y_dimension(_height)

        return (_x, _y, _width, _height)

    def update_box(self):
        """Update size and position from box property"""

        (_x, _y, _width, _height) = self.get_precise_rectangle()

        self.SetSize(_width, _height)
        self.set_pos(_x, _y)

        self.ResetControlPoints()
        self.GetCanvas().Refresh(False)

    def synchronize_box(self):
        """Add self dimensions into box property"""

        _size = self.GetBoundingBoxMin()
        _pos = self.get_pos()

        self.set_value("box", "width", utils.screen_to_dim(_size[0]))
        self.set_value("box", "height", utils.screen_to_dim(_size[1]))
        self.set_value("box", "x", utils.screen_to_dim(_pos[0]))
        self.set_value("box", "y", utils.screen_to_dim(_pos[1]))

        env.OnPropertyListener(self)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if category == "box":
            self.update_box()


FIELD_MAIN = te.Field
DEFAULT_TEXT = "[Empty Field]"
NOT_FOUND_TEXT = "[Data not found]"

class Field(wxogl.TextShape, ShapeBase):
    """Visual field element"""

    def __init__(self, parent_canvas, x, y):
        wxogl.TextShape.__init__(self, DEFAULT_WIDTH, DEFAULT_HEIGHT)
        ShapeBase.__init__(self, FIELD_MAIN, DATA_ZERO_OR_ONE)

        self.init_shape(parent_canvas, x, y)
        self.set_text(DEFAULT_TEXT)

    def set_text(self, text):
        """Set text of field"""

        self.ClearText()
        self.AddText(text)

    def update_text(self):
        """Update text of shape from properties"""

        _expr = self.get_value("field", "expr")
        _pre_data = self.get_value("field", "data")
        if _pre_data:
            _pre_data = env.get_predefined_data(_pre_data)
            if _pre_data:
                _pre_data = _pre_data.get_value("data", self.BODY_PROPERTY)
            else:
                _pre_data = NOT_FOUND_TEXT
        _data = self.get_value("data", self.BODY_PROPERTY)

        if _expr and _expr != "":
            self.set_text(_expr)
        elif _pre_data and _pre_data != "":
            self.set_text(_pre_data)
        elif self.get_value("data", self.EXISTANCE_PROPERTY) and _data != "":
            self.set_text(_data)
        else:
            self.set_text(DEFAULT_TEXT)

        self.GetCanvas().Refresh(False)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        ShapeBase.after_property_changed(self, category, attribute)

        if attribute == "expr" or attribute == "data" or category == "data":
            self.update_text()


LINE_MAIN = te.Line

class Line(wxogl.RectangleShape, ShapeBase):
    """Visual image element"""

    def __init__(self, parent_canvas, x, y):
        wxogl.RectangleShape.__init__(self, DEFAULT_WIDTH, DEFAULT_HEIGHT)
        ShapeBase.__init__(self, LINE_MAIN, [])

        self.init_shape(parent_canvas, x, y)

    def OnDraw(self, dc):
        """Draw line and check if it is backslant"""

        (_left_x, _left_y, _width, _height) = self.get_precise_rectangle()
        (_right_x, _right_y) = (_left_x + _width, _left_y + _height)

        if self.get_value("line", "backslant"):
            dc.DrawLine(_left_x, _left_y, _right_x, _right_y)
        else:
            dc.DrawLine(_left_x, _right_y, _right_x, _left_y)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        ShapeBase.after_property_changed(self, category, attribute)

        if attribute == "backslant":
            self.GetCanvas().Refresh(False)


RECTANGLE_MAIN = te.Rectangle

class Rectangle(wxogl.RectangleShape, ShapeBase):
    """Visual rectangle element"""

    def __init__(self, parent_canvas, x, y):
        wxogl.RectangleShape.__init__(self, DEFAULT_WIDTH, DEFAULT_HEIGHT)
        ShapeBase.__init__(self, RECTANGLE_MAIN, [])

        self.init_shape(parent_canvas, x, y)
        self.update_transparence()

    def update_transparence(self):
        """Update transparence of rectangle from properties"""

        if self.get_value("rectangle", "opaque"):
            self.SetBrush(wx.TRANSPARENT_BRUSH)
        else:
            self.SetBrush(wx.LIGHT_GREY_BRUSH)
        self.GetCanvas().Refresh(False)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        ShapeBase.after_property_changed(self, category, attribute)

        if attribute == "radius":
            self.SetCornerRadius(self.get_value("rectangle", "radius"))
            self.GetCanvas().Refresh(False)

        if attribute == "opaque":
            self.update_transparence()


class ResizableBitmapShape(wxogl.BitmapShape):
    """Resizable image element (original ogl bitmaps aren't resizable)"""

    def __init__(self):
        wxogl.BitmapShape.__init__(self)

        self.original_bitmap = None
        self.size = (DEFAULT_WIDTH, DEFAULT_HEIGHT)

    def SetBitmap(self, bitmap):
        self.original_bitmap = bitmap
        self.resize_bitmap()

    def resize_bitmap(self):
        """Resize and apply bitmap"""

        if not self.original_bitmap:
            return

        (_width, _height) = self.GetSize()
        _scaled = utils.scale_bitmap(self.original_bitmap, _width, _height)
        wxogl.BitmapShape.SetBitmap(self, _scaled)

    def GetSize(self):
        return self.size

    def SetSize(self, width, height):
        """Override BitmapShape's method to implement resizing"""

        (_width, _height) = self.GetSize()

        if self.GetSize() == (width, height):
            wxogl.BitmapShape.SetSize(self, width, height)
        else:
            self.size = (width, height)
            self.resize_bitmap()


DEFAULT_IMAGE = "res/image_default.bmp"
IMAGE_MAIN = te.Image

class Image(ResizableBitmapShape, ShapeBase):
    """Visual image element"""

    def __init__(self, parent_canvas, x, y):
        ResizableBitmapShape.__init__(self)
        ShapeBase.__init__(self, IMAGE_MAIN, DATA_ZERO_OR_ONE)

        _bitmap = wx.Image(DEFAULT_IMAGE, wx.BITMAP_TYPE_BMP).ConvertToBitmap()
        self.SetBitmap(_bitmap)
        self.init_shape(parent_canvas, x, y)


BARCODE_IMAGE = "res/barcode_default.bmp"
BARCODE_MAIN = te.BarCode

class Barcode(ResizableBitmapShape, ShapeBase):
    """Visual barcode element"""

    def __init__(self, parent_canvas, x, y):
        ResizableBitmapShape.__init__(self)
        ShapeBase.__init__(self, BARCODE_MAIN, DATA_ZERO_OR_ONE)

        _bitmap = wx.Image(BARCODE_IMAGE, wx.BITMAP_TYPE_BMP).ConvertToBitmap()
        self.SetBitmap(_bitmap)
        self.init_shape(parent_canvas, x, y)
