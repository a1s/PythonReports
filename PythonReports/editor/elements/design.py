"""Visual design elements, that can be placed in section"""

import os
import re

import PythonReports.template as te
import wx
import wx.lib.ogl as wxogl
from wx.lib.ogl._oglmisc import *
import wx.lib.wordwrap as wxww

from element import Element
from .. import utils


START_SIZE = 50

class DesignPlace(wxogl.ShapeCanvas):
    """Place for painting visual elements"""

    def __init__(self, parent, width, parent_section):
        wxogl.ShapeCanvas.__init__(self, parent, style=wx.NO_BORDER)

        self.app = wx.GetApp()
        self.section = parent_section

        self.SetSize((width, START_SIZE))
        #be careful here with min height.
        #It seems like bug in wx, if it is set SetSize donesn't work,
        #and size is MinSize until events in App are Yielded
        self.SetMinSize((width, -1))
        self.SetMaxSize((width, -1))

        self.diagram = wxogl.Diagram()
        self.SetDiagram(self.diagram)
        self.diagram.SetCanvas(self)

        self.lowest_point = 0
        self.elements = []

    def set_height(self, height):
        """Set height of design place"""

        self.SetSize((self.GetSize().GetWidth(), height))
        self.update_all_boxes()

    def get_lowest_point(self):
        """Get lowest point of all shapes. Counted adding and changing shapes"""

        return self.lowest_point

    def recount_lowest_point(self):
        """Count lowest shape and get it lowest point"""

        _old_lowest = self.lowest_point
        self.lowest_point = 0

        for _shape in self.get_all_shapes():
                self.recount_shape_lowest(_shape)

        #call section's update height to adjust it to lowest point update
        if self.lowest_point <> _old_lowest:
            self.section.update_height()

    def recount_shape_lowest(self, shape):
        """Recount lowest point of one shape"""

        _shape_lowest = shape.get_lowest_point()
        if _shape_lowest > self.lowest_point:
            self.lowest_point = _shape_lowest

    def set_width(self, width):
        """Set min, max and actual width of design place"""

        self.SetSize((width, self.GetSize().GetHeight()))
        self.SetMinSize((width, -1))
        self.SetMaxSize((width, -1))

        self.update_all_boxes()

    def OnLeftClick(self, x, y, keys):
        """Create new elements if needed"""
        self.app.focus_remove()

        _class_to_create = self.app.design_tool_get().element_class
        if _class_to_create:
            self.add_element(_class_to_create(self, x, y))
            self.app.design_tool_set(DESIGN_TOOLS["Select"])

    def get_all_shapes(self):
        """Get list of all shapes"""

        return self.elements

    def add_element(self, element):
        """Add new element to this DesignPlace"""

        self.elements.append(element)
        self.app.focus_set(element)
        self.Refresh(False)

        self.recount_lowest_point()

    def move_shape(self, shape, pos, diag_pos):
        """Move shape to given position in lists"""

        self.elements.remove(shape)
        self.diagram.RemoveShape(shape)

        self.elements.insert(pos, shape)
        self.diagram._shapeList.insert(diag_pos, shape)
        self.Refresh(False)

    def move_up_shape(self, shape):
        """Move the shape up by z axis"""

        _old_index_of_shape = self.elements.index(shape)
        if _old_index_of_shape < len(self.elements) - 1:
            _diag_pos = self.diagram._shapeList.index(shape) + 1
            self.move_shape(shape, _old_index_of_shape + 1, _diag_pos)

    def move_down_shape(self, shape):
        """Move the shape down by z axis"""

        _old_index_of_shape = self.elements.index(shape)
        if _old_index_of_shape > 0:
            _diag_pos = self.diagram._shapeList.index(shape) - 1
            self.move_shape(shape, _old_index_of_shape - 1, _diag_pos)

    def delete_element(self, element):
        """Delete element from DesignPlace"""

        self.elements.remove(element)
        self.RemoveShape(element)
        self.Refresh(False)

        self.recount_lowest_point()

    def update_all_boxes(self):
        """Update boxes of all elements in design place"""

        for _shape in self.get_all_shapes():
            _shape.update_box()

    def force_data_update(self):
        """Update all elements that are linked to report data"""

        for _shape in self.get_all_shapes():
            if isinstance(_shape, Field):
                _shape.update_text()
            elif isinstance(_shape, Image):
                _shape.update_picture()


class AllShapesEvtHandler(wxogl.ShapeEvtHandler):
    """Listener for all shapes' events. All methods are overrided"""

    def __init__(self):
        wxogl.ShapeEvtHandler.__init__(self)

        self.app = wx.GetApp()

    def OnLeftClick(self, x, y, keys=0, attach=0):
        _shape = self.GetShape()
        if self.app.design_tool_get() == DESIGN_TOOLS["Select"]:
            self.app.focus_set(_shape)
        else:
            _shape.GetCanvas().OnLeftClick(x, y, keys)

    def OnBeginDragLeft(self, x, y, keys, attach):
        self.app.toggle_double_buffering(False)

        self.GetPreviousHandler().OnBeginDragLeft(x, y, keys, attach)

        _shape = self.GetShape()
        if not _shape.Selected():
            self.OnLeftClick(x, y, keys, attach)

    def OnEndDragLeft(self, x, y, keys=0, attach=0):
        self.app.toggle_double_buffering(True)

        self.GetPreviousHandler().OnEndDragLeft(x, y, keys, attach)
        self.GetShape().synchronize_box()

    def OnSizingBeginDragLeft(self, pt, x, y, keys, attach):
        self.app.toggle_double_buffering(False)

        self.GetPreviousHandler().OnSizingBeginDragLeft(pt, x, y, keys, attach)

    def OnSizingEndDragLeft(self, pt, x, y, keys, attach):
        self.app.toggle_double_buffering(True)

        self.GetPreviousHandler().OnSizingEndDragLeft(pt, x, y, keys, attach)
        self.GetShape().synchronize_box()

    def OnMovePost(self, dc, x, y, oldX, oldY, display):
        self.GetPreviousHandler().OnMovePost(dc, x, y, oldX, oldY, display)

        #fix bug on MacOS
        if "wxMac" in wx.PlatformInfo:
            _shape = self.GetShape()
            _shape.GetCanvas().Refresh(False)


BOX_ONE = [te.Box]
DATA_ZERO_OR_ONE = [te.Data]
STYLE_UNRESTRICTED = [te.Style]

DEFAULT_WIDTH = 100
DEFAULT_HEIGHT = 40

class ShapeBase(Element):
    """Methods for all shapes"""

    def __init__(self, main_val, zero_or_one_val, min_size=(-1, -1)):
        Element.__init__(self, main_val, zero_or_one_val, BOX_ONE,
            STYLE_UNRESTRICTED)

        self.min_size = min_size
        self.app = wx.GetApp()

    def get_control_point_offsets(self):
        """Get offsets of control point from center of shape"""

        _maxX, _maxY = self.GetBoundingBoxMax()
        _minX, _minY = self.GetBoundingBoxMin()

        _widthMin = _minX - CONTROL_POINT_SIZE + 2
        _heightMin = _minY - CONTROL_POINT_SIZE + 2

        # Offsets from main object
        return (-_heightMin / 2.0, _heightMin / 2.0 + (_maxY - _minY),
            - _widthMin / 2.0, _widthMin / 2.0 + (_maxX - _minX))

    def MakeControlPoints(self):
        """Override Shape's method

        @note: control points must be created inside object, not outside it

        """
        _top, _bottom, _left, _right = self.get_control_point_offsets()

        CONTROL_POINTS = [
            (_left, _top, CONTROL_POINT_DIAGONAL),
            (_right, _top, CONTROL_POINT_DIAGONAL),
            (_left, _bottom, CONTROL_POINT_DIAGONAL),
            (_right, _bottom, CONTROL_POINT_DIAGONAL),
            (0, _top, CONTROL_POINT_VERTICAL),
            (0, _bottom, CONTROL_POINT_VERTICAL),
            (_right, 0, CONTROL_POINT_HORIZONTAL),
            (_left, 0, CONTROL_POINT_HORIZONTAL),
        ]

        for _point_param in CONTROL_POINTS:
            _point = wxogl.ControlPoint(self._canvas, self, CONTROL_POINT_SIZE,
                _point_param[0], _point_param[1], _point_param[2])
            self._canvas.AddShape(_point)
            self._controlPoints.append(_point)

    def ResetControlPoints(self):
        """Override Shape's method

        @note: control points must be created inside object, not outside it

        """
        self.ResetMandatoryControlPoints()

        if len(self._controlPoints) == 0:
            return

        _top, _bottom, _left, _right = self.get_control_point_offsets()

        POINT_OFFSETS = (
            (_left, _top), (_right, _top), (_left, _bottom), (_right, _bottom),
            (0, _top), (0, _bottom), (_right, 0), (_left, 0)
        )

        for _point_id in range(8):
            self._controlPoints[_point_id]._xoffset \
                = POINT_OFFSETS[_point_id][0]
            self._controlPoints[_point_id]._yoffset \
                = POINT_OFFSETS[_point_id][1]

    def init_shape(self, parent_canvas, x, y, sync_box):
        """Setup settings for shape

        @param sync_box: if set to true shape params will be applied to box

        """
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

        if sync_box:
            self.synchronize_box()
        else:
            self.update_box()

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

    def move_up(self):
        """Move shape by z axis "up" from display"""

        self.GetCanvas().move_up_shape(self)

    def move_down(self):
        """Move shape by z axis "down" into display"""

        self.GetCanvas().move_down_shape(self)

    def delete(self):
        """Delete this element from Design place"""

        self.GetCanvas().delete_element(self)

    def get_lowest_point(self):
        """Get lowest point of shape (y + height) Return 0 if dims < 0"""

        (_x, _y) = self.get_box_screen_coords()
        (_width, _height) = self.get_box_screen_dims()

        if _y < 0 or _height < 0:
            return 0
        else:
            return _y + _height

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

    def get_vert_alignment(self):
        """Get wx.ALIGN_ from box properties"""

        V_FLAGS_LINK = {
            "top": wx.ALIGN_TOP,
            "center": wx.ALIGN_CENTER_VERTICAL,
            "bottom": wx.ALIGN_BOTTOM,
        }

        return V_FLAGS_LINK[self.get_value("box", "valign")]

    def get_hor_alignment(self):
        H_FLAGS_LINK = {
            "left": wx.ALIGN_LEFT,
            "center": wx.ALIGN_CENTER_HORIZONTAL,
            "right": wx.ALIGN_RIGHT,
        }

        return H_FLAGS_LINK[self.get_value("box", "halign")]

    def correct_dim_pair(self, coord, dim, max_dim):
        """Count x and width using offset if negative values"""

        if coord < 0:
            coord = max_dim + coord

        if dim < 0:
            dim = max_dim + dim - coord

        return (coord, dim)

    def get_box_screen_coords(self):
        """Get x and y from box converted to screen coords"""

        return (utils.dim_to_screen(self.get_value("box", "x")),
            utils.dim_to_screen(self.get_value("box", "y")))

    def get_box_screen_dims(self):
        """Get width and height from box converted to screen coords"""

        return (utils.dim_to_screen(self.get_value("box", "width")),
            utils.dim_to_screen(self.get_value("box", "height")))

    def get_precise_rectangle(self):
        """Get bounding box of line from properties - more precise than shapes
        """

        (_x, _y) = self.get_box_screen_coords()
        (_width, _height) = self.get_box_screen_dims()

        _size = self.GetCanvas().GetSize()
        (_x, _width) = self.correct_dim_pair(_x, _width, _size.GetWidth())
        (_y, _height) = self.correct_dim_pair(_y, _height, _size.GetHeight())

        return (_x, _y, _width, _height)

    def update_box(self):
        """Update size and position from box property"""

        (_x, _y, _width, _height) = self.get_precise_rectangle()

        if _width < self.min_size[0]:
            _width = self.min_size[0]
        if _height < self.min_size[1]:
            _height = self.min_size[1]

        self.SetSize(_width, _height)
        self.set_pos(_x, _y)

        self.ResetControlPoints()
        self.GetCanvas().recount_lowest_point()
        self.GetCanvas().Refresh(False)

    def synchronize_box(self):
        """Add self dimensions into box property"""

        _size = self.get_size()
        _pos = self.get_pos()

        self.set_value("box", "width", utils.screen_to_dim(_size[0]))
        self.set_value("box", "height", utils.screen_to_dim(_size[1]))
        self.set_value("box", "x", utils.screen_to_dim(_pos[0]))
        self.set_value("box", "y", utils.screen_to_dim(_pos[1]))

        self.app.focus_set(self)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if category == "box":
            self.update_box()


FIELD_MAIN = te.Field
FIELD_MIN_HEIGHT = 12
DEFAULT_FONT_SIZE = 8
DEFAULT_TEXT = "[Empty Field]"
NOT_FOUND_TEXT = "[Data not found]"
EXPRESSION_TEXT = "%EX"

class Field(ShapeBase, wxogl.TextShape):
    """Visual field element"""

    def __init__(self, parent_canvas, x, y, sync_box=True):
        wxogl.TextShape.__init__(self, DEFAULT_WIDTH, DEFAULT_HEIGHT)
        ShapeBase.__init__(self, FIELD_MAIN, DATA_ZERO_OR_ONE,
            min_size=(-1, FIELD_MIN_HEIGHT))

        self.init_shape(parent_canvas, x, y, sync_box)
        self.set_text(DEFAULT_TEXT)

    format_escape_chars = re.compile("%[d,i,o,u,x,X,e,E,f,F,g,G,c,r,s]")

    def OnDraw(self, dc):
        """Draw formated text and align it"""

        (_x, _y) = self.get_pos()
        (_width, _height) = self.get_size()
        _shape_rect = wx.Rect(_x, _y, _width, _height)

        #TODO: Apply font from active style
        _font = wx.Font(DEFAULT_FONT_SIZE * self.app.zoom_get(),
            wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)
        dc.SetFont(_font)

        _format_string = self.get_value("field", "format")
        _format_string = self.format_escape_chars.sub("{0}", _format_string)
        _format_string.replace("%%", "%")
        _text = _format_string.format(self.text)
        _text = wxww.wordwrap(_text, _width, dc)

        dc.SetClippingRect(_shape_rect)
        dc.DrawLabel(_text, _shape_rect, self.get_text_alignment())
        dc.DestroyClippingRegion()

    def set_text(self, text):
        """Set text of field"""

        self.text = text

    def get_text_alignment(self):
        """Get real alignment of text form box and field"""

        TEXT_FLAGS_LINK = {
            "left": wx.ALIGN_LEFT,
            "center": wx.ALIGN_CENTER_HORIZONTAL,
            "right": wx.ALIGN_RIGHT,
            "justified": wx.ALIGN_CENTER_HORIZONTAL,
        }

        _h_align = self.get_value("field", "align")
        if _h_align == "left":
            _h_align = self.get_hor_alignment()
        else:
            _h_align = TEXT_FLAGS_LINK[self.get_value("field", "align")]

        return self.get_vert_alignment() | _h_align

    def update_text(self):
        """Update text of shape from properties"""

        _expr = self.get_value("field", "expr")
        _pre_data = self.get_value("field", "data")
        if _pre_data:
            _pre_data = self.app.get_predefined_data(_pre_data)
            if _pre_data:
                _pre_data = _pre_data.get_value("data", self.BODY_PROPERTY)
            else:
                _pre_data = NOT_FOUND_TEXT
        _data = self.get_value("data", self.BODY_PROPERTY)

        if _expr and _expr != "":
            self.set_text(EXPRESSION_TEXT)
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

        if attribute == "expr" or attribute == "data" or category == "data" \
        or attribute == "format" or category == "box":
            self.update_text()


LINE_MAIN = te.Line

class Line(ShapeBase, wxogl.RectangleShape):
    """Visual image element"""

    def __init__(self, parent_canvas, x, y, sync_box=True):
        wxogl.RectangleShape.__init__(self, DEFAULT_WIDTH, DEFAULT_HEIGHT)
        ShapeBase.__init__(self, LINE_MAIN, [])

        self.init_shape(parent_canvas, x, y, sync_box)

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

class Rectangle(ShapeBase, wxogl.RectangleShape):
    """Visual rectangle element"""

    def __init__(self, parent_canvas, x, y, sync_box=True):
        wxogl.RectangleShape.__init__(self, DEFAULT_WIDTH, DEFAULT_HEIGHT)
        ShapeBase.__init__(self, RECTANGLE_MAIN, [])

        self.init_shape(parent_canvas, x, y, sync_box)
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
        self.rotated_bitmap = None

        self.vertical = False
        self.size = (DEFAULT_WIDTH, DEFAULT_HEIGHT)

    def SetBitmap(self, bitmap):
        self.original_bitmap = bitmap
        self.rotate_bitmap()
        self.resize_bitmap()

    def SetImage(self, image):
        self.SetBitmap(wx.BitmapFromImage(image))

    def SetFilename(self, file_name, file_type=wx.BITMAP_TYPE_BMP):
        self.file_name = file_name
        _bitmap = wx.Image(file_name, file_type).ConvertToBitmap()
        self.SetBitmap(_bitmap)

    def GetFilename(self):
        return self.file_name

    def rotate_bitmap(self):
        """Rotate original bitmap and save it"""

        if not self.original_bitmap:
            return

        if self.is_vertical():
            self.rotated_bitmap = \
                utils.rotate90_bitmap(self.original_bitmap, True)
        else:
            self.rotated_bitmap = self.original_bitmap

    def set_vertical(self, vertical):
        """Rotate this image by 90 degrees or not"""

        self.vertical = vertical
        self.rotate_bitmap()
        self.resize_bitmap()

    def is_vertical(self):
        """Get is this image is rotated by 90 degrees"""
        return self.vertical

    def resize_bitmap(self):
        """Resize rotated bitmap and apply it"""

        if not self.rotated_bitmap:
            return

        (_width, _height) = self.GetSize()
        _scaled = utils.scale_bitmap(self.rotated_bitmap, _width, _height)
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


DEFAULT_IMAGE = utils.get_resource_img("image_default")
ERROR_IMAGE = utils.get_resource_img("image_error")
IMAGE_MAIN = te.Image

class Image(ShapeBase, ResizableBitmapShape):
    """Visual image element"""

    TYPES_LINK = {
        "png" : wx.BITMAP_TYPE_PNG,
        "jpeg" : wx.BITMAP_TYPE_JPEG,
        "gif" : wx.BITMAP_TYPE_GIF,
    }

    def __init__(self, parent_canvas, x, y, sync_box=True):
        ResizableBitmapShape.__init__(self)
        ShapeBase.__init__(self, IMAGE_MAIN, DATA_ZERO_OR_ONE)

        self.SetImage(DEFAULT_IMAGE)
        self.init_shape(parent_canvas, x, y, sync_box)

    def update_picture(self):
        """Update picture from properties"""

        _file_name = self.get_value("image", "file")

        if _file_name is None or _file_name == "":
            self.SetImage(DEFAULT_IMAGE)
        else:
            _type = self.get_value("image", "type")

            if not os.path.isabs(_file_name):
                _file_name = os.path.join(self.app.get_work_dir(), _file_name)

            try:
                self.SetFilename(_file_name, self.TYPES_LINK[_type])
            except:
                self.SetImage(ERROR_IMAGE)

        self.GetCanvas().Refresh(False)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        ShapeBase.after_property_changed(self, category, attribute)

        if attribute == "file" or attribute == "type":
            self.update_picture()


BARCODE_IMAGE = utils.get_resource_img("barcode_default")
BARCODE_MAIN = te.BarCode

class Barcode(ShapeBase, ResizableBitmapShape):
    """Visual barcode element"""

    BARCODE_WIDTH = 50
    BARCODE_HEIGHT = 20

    def __init__(self, parent_canvas, x, y, sync_box=True):
        ResizableBitmapShape.__init__(self)
        ShapeBase.__init__(self, BARCODE_MAIN, DATA_ZERO_OR_ONE)

        self.SetImage(BARCODE_IMAGE)
        self.init_shape(parent_canvas, x, y, sync_box)

    def get_box_screen_dims(self):
        """Ignore box size for barcode"""

        return (self.BARCODE_WIDTH * self.app.zoom_get(),
            self.BARCODE_HEIGHT * self.app.zoom_get())

    def update_orientation(self):
        """Update orientation from properties"""

        if self.get_value("barcode", "vertical"):
            self.set_vertical(True)
        else:
            self.set_vertical(False)
        self.GetCanvas().Refresh(False)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        ShapeBase.after_property_changed(self, category, attribute)

        if attribute == "vertical":
            self.update_orientation()


class DESIGN_TOOL(object):
    """Contain info about tools"""

    def __init__(self, id, el_class):
        self.id = id
        self.element_class = el_class

DESIGN_TOOLS = {
    "Select" : DESIGN_TOOL(1, None),
    "Field" : DESIGN_TOOL(2, Field),
    "Line" : DESIGN_TOOL(3, Line),
    "Rectangle" : DESIGN_TOOL(4, Rectangle),
    "Image" : DESIGN_TOOL(5, Image),
    "Barcode" : DESIGN_TOOL(6, Barcode)
}

# vim: set et sts=4 sw=4 :
