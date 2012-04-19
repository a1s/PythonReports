"""Visual design elements, that can be placed in section"""
"""
13-apr-2012 [kacah]    Added Line, Rectangle, Image, Barcode
11-apr-2012 [kacah]    Subreport moved to section.py, added EventsHandler,
                       added DesignPlace, added Field
03-apr-2012 [kacah]    created, added Subreport

"""
import os
import re

import PythonReports.template as te
import wx
import wx.lib.ogl as wxogl
import wx.lib.wordwrap as wxww

from elements.element import Element
import utils


MIN_SIZE = 10

class DesignPlace(wxogl.ShapeCanvas):
    """Place for painting visual elements"""

    def __init__(self, parent, width):
        wxogl.ShapeCanvas.__init__(self, parent, size=(width, MIN_SIZE),
            style=wx.NO_BORDER)

        self.app = wx.GetApp()

        self.SetMinSize((width, MIN_SIZE))
        self.SetMaxSize((width, -1))

        self.diagram = wxogl.Diagram()
        self.SetDiagram(self.diagram)
        self.diagram.SetCanvas(self)

        self.init_lists()

    def init_lists(self):
        """Setup lists for all types of elements"""

        self.elements = {}
        self.elements[Field] = []
        self.elements[Rectangle] = []
        self.elements[Image] = []
        self.elements[Barcode] = []
        self.elements[Line] = []

    def set_height(self, height):
        """Set height of design place"""

        self.SetSize((self.GetSize().GetWidth(), height))

    def set_width(self, width):
        """Set min, max and actual width of design place"""

        self.SetSize((width, self.GetSize().GetHeight()))
        self.SetMinSize((width, MIN_SIZE))
        self.SetMaxSize((width, -1))

        self.update_all_boxes()

    def OnLeftClick(self, x, y, keys):
        """Create new elements if needed"""
        self.app.remove_focus()

        _class_to_create = self.app.get_active_design_tool().element_class
        if _class_to_create:
            self.add_element(_class_to_create(self, x, y))

    def add_element(self, element):
        """Add new element to this DesignPlace"""

        self.elements[element.__class__].append(element)
        self.app.set_focus(element)
        self.Refresh(False)

    def delete_element(self, element):
        """Delete element from DesignPlace"""

        self.elements[element.__class__].remove(element)
        self.RemoveShape(element)
        self.Refresh(False)

    def update_all_boxes(self):
        """Update boxes of all elements in design place"""

        for (_el_class, _el_list) in self.elements.items():
            for _elem in _el_list:
                _elem.update_box()

    def force_data_update(self):
        """Update all elements that are linked to report data"""

        for _field in self.elements[Field]:
            _field.update_text()
        for _image in self.elements[Image]:
            _image.update_picture()


class AllShapesEvtHandler(wxogl.ShapeEvtHandler):
    """Listener for all shapes' events. All methods are overrided"""

    def __init__(self):
        wxogl.ShapeEvtHandler.__init__(self)

        self.app = wx.GetApp()

    def OnLeftClick(self, x, y, keys=0, attach=0):
        shape = self.GetShape()
        self.app.set_focus(shape)

    def OnBeginDragLeft(self, x, y, keys, attach):
        self.app.toggle_double_buffering(False)

        self.GetPreviousHandler().OnBeginDragLeft(x, y, keys, attach)

        shape = self.GetShape()
        if not shape.Selected():
            self.OnLeftClick(x, y, keys, attach)

    def OnEndDragLeft(self, x, y, keys=0, attach=0):
        self.GetPreviousHandler().OnEndDragLeft(x, y, keys, attach)

        self.GetShape().synchronize_box()
        self.app.toggle_double_buffering(True)

    def OnSizingBeginDragLeft(self, pt, x, y, keys, attach):
        self.app.toggle_double_buffering(False)

        self.GetPreviousHandler().OnSizingBeginDragLeft(pt, x, y, keys, attach)

    def OnSizingEndDragLeft(self, pt, x, y, keys, attach):
        self.GetPreviousHandler().OnSizingEndDragLeft(pt, x, y, keys, attach)

        self.GetShape().synchronize_box()
        self.app.toggle_double_buffering(True)

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

        self.app = wx.GetApp()

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

    def delete(self):
        """Delete this element from Design place"""

        self.GetCanvas().delete_element(self)

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
        """Get bounding box of line from properties - more precise than shapes"""

        (_x, _y) = self.get_box_screen_coords()
        (_width, _height) = self.get_box_screen_dims()

        _size = self.GetCanvas().GetSize()
        (_x, _width) = self.correct_dim_pair(_x, _width, _size.GetWidth())
        (_y, _height) = self.correct_dim_pair(_y, _height, _size.GetHeight())

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

        self.app.set_focus(self)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if category == "box":
            self.update_box()


FIELD_MAIN = te.Field
FIELD_MIN_HEIGHT = 12
DEFAULT_TEXT = "[Empty Field]"
NOT_FOUND_TEXT = "[Data not found]"
EXPRESSION_TEXT = "%EX"

class Field(wxogl.TextShape, ShapeBase):
    """Visual field element"""

    def __init__(self, parent_canvas, x, y, sync_box=True):
        wxogl.TextShape.__init__(self, DEFAULT_WIDTH, DEFAULT_HEIGHT)
        ShapeBase.__init__(self, FIELD_MAIN, DATA_ZERO_OR_ONE)

        self.init_shape(parent_canvas, x, y, sync_box)
        self.set_text(DEFAULT_TEXT)

    format_escape_chars = re.compile("%[d,i,o,u,x,X,e,E,f,F,g,G,c,r,s]")

    def OnDraw(self, dc):
        """Draw formated text and align it"""

        (_left_x, _left_y, _width, _height) = self.get_precise_rectangle()
        _shape_rect = wx.Rect(_left_x, _left_y, _width, _height)

        _font = wx.Font(8, wx.NORMAL, wx.NORMAL, wx.NORMAL)
        dc.SetFont(_font)

        _format_string = self.get_value("field", "format")
        _format_string = self.format_escape_chars.sub("{0}", _format_string)
        _format_string.replace("%%", "%")
        _text = _format_string.format(self.text)
        _text = wxww.wordwrap(_text, _width, dc)

        dc.SetClippingRect(_shape_rect)
        dc.DrawLabel(_text, wx.Rect(_left_x, _left_y, _width, _height),
            self.get_text_alignment())
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

    def check_min_size(self):
        """If this shape < FIELD_MIN_HEIGHT grow it"""

        if self.get_size()[1] < FIELD_MIN_HEIGHT:
            self.SetSize(self.get_size()[0], FIELD_MIN_HEIGHT)
            self.synchronize_box()

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        ShapeBase.after_property_changed(self, category, attribute)

        if attribute == "expr" or attribute == "data" or category == "data" \
        or attribute == "format":
            self.update_text()

        if category == "box" and attribute == "height":
            self.check_min_size()


LINE_MAIN = te.Line

class Line(wxogl.RectangleShape, ShapeBase):
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

class Rectangle(wxogl.RectangleShape, ShapeBase):
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


DEFAULT_IMAGE = "res/image_default.bmp"
ERROR_IMAGE = "res/image_error.bmp"
IMAGE_MAIN = te.Image

class Image(ResizableBitmapShape, ShapeBase):
    """Visual image element"""

    TYPES_LINK = {
        "png" : wx.BITMAP_TYPE_PNG,
        "jpeg" : wx.BITMAP_TYPE_JPEG,
        "gif" : wx.BITMAP_TYPE_GIF,
    }

    def __init__(self, parent_canvas, x, y, sync_box=True):
        ResizableBitmapShape.__init__(self)
        ShapeBase.__init__(self, IMAGE_MAIN, DATA_ZERO_OR_ONE)

        self.SetFilename(DEFAULT_IMAGE)
        self.init_shape(parent_canvas, x, y, sync_box)

    def update_picture(self):
        """Update picture from properties"""

        _file_name = self.get_value("image", "file")

        if _file_name is None or _file_name == "":
            self.SetFilename(DEFAULT_IMAGE)
        else:
            _type = self.get_value("image", "type")

            if not os.path.isabs(_file_name):
                _file_name = os.path.join(self.app.get_work_dir(), _file_name)

            try:
                self.SetFilename(_file_name, self.TYPES_LINK[_type])
            except:
                self.SetFilename(ERROR_IMAGE)

        self.GetCanvas().Refresh(False)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        ShapeBase.after_property_changed(self, category, attribute)

        if attribute == "file" or attribute == "type":
            self.update_picture()


BARCODE_IMAGE = "res/barcode_default.bmp"
BARCODE_MAIN = te.BarCode

class Barcode(ResizableBitmapShape, ShapeBase):
    """Visual barcode element"""

    BARCODE_WIDTH = 50
    BARCODE_HEIGHT = 20

    def __init__(self, parent_canvas, x, y, sync_box=True):
        ResizableBitmapShape.__init__(self)
        ShapeBase.__init__(self, BARCODE_MAIN, DATA_ZERO_OR_ONE)

        self.SetFilename(BARCODE_IMAGE)
        self.init_shape(parent_canvas, x, y, sync_box)
        self.SetFixedSize(self.BARCODE_WIDTH, self.BARCODE_HEIGHT)

    def get_box_screen_dims(self):
        """Ignore box size for barcode"""

        return (self.BARCODE_WIDTH, self.BARCODE_HEIGHT)

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
