"""Main menu of editor"""
"""
18-apr-2012 [kacah]   created

"""
import wx

class MainMenu(wx.MenuBar):
    """Main menu of editor"""

    new_id = wx.NewId()
    open_id = wx.NewId()
    save_id = wx.NewId()
    move_up_id = wx.NewId()
    move_down_id = wx.NewId()
    delete_id = wx.NewId()
    zoom_in_id = wx.NewId()
    zoom_out_id = wx.NewId()

    MENUS = [
        ("&File", [
            (new_id, "New", "Create new report", "self.OnNew"),
            (open_id, "Open", "Open existing report", "self.OnOpen"),
            (save_id, "Save", "Save current report", "self.OnSave"),
            None,
            (wx.ID_EXIT, "Exit", "Exit the editor", "self.OnExit"),
        ]),
        ("&Edit", [
            (move_up_id, "Move up", "Move shape up", "self.OnMoveUp"),
            (move_down_id, "Move down", "Move shape down", "self.OnMoveDown"),
            None,
            (delete_id, "Delete", "Delete current element", "self.OnDelete"),
        ]),
        ("&View", [
            (zoom_in_id, "Zoom In", "Zoom in workspace", "self.OnZoomIn"),
            (zoom_out_id, "Zoom Out", "Zoom out workspace", "self.OnZoomOut"),
        ]),
        ("&Help", [
            (wx.ID_ABOUT, "About", "About the editor", "self.OnAbout"),
        ]),
    ]

    shortcuts = wx.AcceleratorTable([
        (wx.ACCEL_CTRL, ord('N'), new_id),
        (wx.ACCEL_CTRL, ord('S'), save_id),
        (wx.ACCEL_CTRL, wx.WXK_NUMPAD_ADD, zoom_in_id),
        (wx.ACCEL_CTRL, wx.WXK_NUMPAD_SUBTRACT, zoom_out_id),
        (wx.ACCEL_CTRL, wx.WXK_PAGEUP, move_up_id),
        (wx.ACCEL_CTRL, wx.WXK_PAGEDOWN, move_down_id),
        (wx.ACCEL_NORMAL, wx.WXK_DELETE, delete_id),
    ])


    def __init__(self, main_frame):
        wx.MenuBar.__init__(self)

        self.app = wx.GetApp()

        for _top_menu in self.MENUS:
            _main_menu = wx.Menu()
            for _menu in _top_menu[1]:
                if _menu:
                    self.create_simple_menu(main_frame, _main_menu, _menu)
                else:
                    self.create_separator(_main_menu)
            self.Append(_main_menu, _top_menu[0])

        main_frame.SetAcceleratorTable(self.shortcuts)

    def create_simple_menu(self, frame, main_menu, params):
        """Create simple clickable menu item"""

        (_id, _title, _help, _bind) = params

        _menu_item = main_menu.Append(_id, _title, _help)
        frame.Bind(wx.EVT_MENU, eval(_bind), _menu_item)

    def create_separator(self, main_menu):
        """Create separator item"""

        main_menu.AppendSeparator()

    def OnExit(self, evt):
        self.app.app_close()

    def OnAbout(self, evt):
        pass

    def OnZoomIn(self, evt):
        self.app.zoom_in()

    def OnZoomOut(self, evt):
        self.app.zoom_out()

    def OnNew(self, evt):
        self.app.report_new()

    def OnOpen(self, evt):
        self.app.report_open()

    def OnSave(self, evt):
        self.app.report_save()

    def OnDelete(self, evt):
        self.app.focus_delete()

    def OnMoveUp(self, evt):
        self.app.focus_move_up()

    def OnMoveDown(self, evt):
        self.app.focus_move_down()
