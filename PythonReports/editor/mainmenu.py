"""Main menu of editor"""

import wx

class MainMenu(wx.MenuBar):
    """Main menu of editor"""

    new_id = wx.NewId()
    open_id = wx.NewId()
    save_id = wx.NewId()
    save_as_id = wx.NewId()
    move_up_id = wx.NewId()
    move_down_id = wx.NewId()
    delete_id = wx.NewId()
    zoom_in_id = wx.NewId()
    zoom_out_id = wx.NewId()
    preview_id = wx.NewId()
    write_prp_id = wx.NewId()
    write_pdf_id = wx.NewId()

    MENUS = [
        ("&File", [
            (new_id, "&New\tCtrl+N", "Create new report", "OnNew"),
            (open_id, "&Open\tCtrl+O", "Open existing report", "OnOpen"),
            (save_id, "&Save\tCtrl+S", "Save current report", "OnSave"),
            (save_as_id, "Save &As...",
                "Save current report under a new name", "OnSaveAs"),
            None,
            (wx.ID_EXIT, "&Exit", "Exit the editor", "OnExit"),
        ]),
        ("&Edit", [
            (move_up_id, "Move up\tCtrl+PgUp",
                "Move shape up", "OnMoveUp"),
            (move_down_id, "Move down\tCtrl+PgDown",
                "Move shape down", "OnMoveDown"),
            None,
            (delete_id, "&Delete\tDelete",
                "Delete current element", "OnDelete"),
        ]),
        ("&View", [
            (zoom_in_id, "Zoom &In\tCtrl+Num +",
                "Zoom in workspace", "OnZoomIn"),
            (zoom_out_id, "Zoom &Out\tCtrl+Num -",
                "Zoom out workspace", "OnZoomOut"),
        ]),
        ("&Run", [
            (preview_id, "Pre&view", "Open Report Preview window",
                "OnPreview"),
            (write_prp_id, "Write &XML...",
                "Build Report Printout for shell data and save to an XML file",
                "OnWritePrp"),
            (write_pdf_id, "Write &PDF...",
                "Build Report Printout for shell data and save to PDF file",
                "OnWritePdf"),
        ]),
        ("&Help", [
            (wx.ID_ABOUT, "About", "About the editor", "OnAbout"),
        ]),
    ]

    shortcuts = wx.AcceleratorTable([
        (wx.ACCEL_CTRL, ord('N'), new_id),
        (wx.ACCEL_CTRL, ord('O'), open_id),
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
        (_id, _title, _help, _handler) = params
        _menu_item = main_menu.Append(_id, _title, _help)
        frame.Bind(wx.EVT_MENU, getattr(self, _handler), _menu_item)

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

    def OnSaveAs(self, evt):
        self.app.report_save_file()

    def OnDelete(self, evt):
        self.app.focus_delete()

    def OnMoveUp(self, evt):
        self.app.focus_move_up()

    def OnMoveDown(self, evt):
        self.app.focus_move_down()

    def OnPreview(self, evt):
        self.app.report_preview()

    def OnWritePrp(self, evt):
        self.app.report_write_printout()

    def OnWritePdf(self, evt):
        self.app.report_write_pdf()

# vim: set et sts=4 sw=4 :
