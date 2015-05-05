"""Tree for displaying all elements"""
"""
23-apr-2012 [kacah]   created

"""
import wx
import wx.lib.agw.customtreectrl as wxctree

from elements.section import Section
from elements.container import Container

SELECTION_COLOR = "Black"
BACKGROUND_COLOR = "White"

class ElementsTree(wxctree.CustomTreeCtrl):
    """Tree control for displaying items"""

    def __init__(self, parent):
        wxctree.CustomTreeCtrl.__init__(self, parent, wx.ID_ANY,
            size=wx.Size(200, -1), style=wx.SUNKEN_BORDER,
            agwStyle=wxctree.TR_HAS_BUTTONS | wxctree.TR_FULL_ROW_HIGHLIGHT |
            wxctree.TR_ROW_LINES | wxctree.TR_LINES_AT_ROOT)

        self.SetHilightFocusColour(SELECTION_COLOR)
        self.SetHilightNonFocusColour(SELECTION_COLOR)
        self.SetBackgroundColour(BACKGROUND_COLOR)

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnItemActivated)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnItemExpanded)
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnItemCollapsed)

        self.update_in_process = False
        self.has_selection = False

    def OnItemActivated(self, evt):
        if self.update_in_process:
            return

        _element = self.GetPyData(evt.GetItem())
        self.has_selection = True
        wx.GetApp().focus_set(_element, False)

    def OnItemExpanded(self, evt):
        """Expand section if tree is not in update"""

        if self.update_in_process:
            return

        _element = self.GetPyData(evt.GetItem())
        _element.Expand()
        _element.OnExpandedCollapsed(evt)

    def OnItemCollapsed(self, evt):
        """Collapse section if tree is not in update"""

        if self.update_in_process:
            return

        _element = self.GetPyData(evt.GetItem())
        _element.Collapse()
        _element.OnExpandedCollapsed(evt)

    def check_selected(self, tree_elem, report_elem):
        """Check if report_elem is focused than select tree_elem"""

        if wx.GetApp().focus_get() is report_elem:
            self.SelectItem(tree_elem, True)
            self.has_selection = True

    def build_report_items(self, report):
        """Build tree elements from report"""

        self.update_in_process = True
        self.has_selection = False

        self.DeleteAllItems()

        if report is None:
            return

        _tree_root = self.AddRoot(report.get_title())
        self.SetPyData(_tree_root, report)
        self.build_sections(_tree_root, report)

        if report.IsExpanded():
            self.Expand(_tree_root)
        self.check_selected(_tree_root, report)

        self.update_in_process = False

    def build_sections(self, tree_root, report):
        """Build all section in tree"""

        for _section in report.listeners_list:
            _tree_section = self.AppendItem(tree_root, _section.get_title())
            self.SetPyData(_tree_section, _section)
            #check if this is really section. It may be button or something else.
            if isinstance(_section, Section):
                self.build_section_items(_tree_section, _section)

            if isinstance(_section, Container):
                if _section.IsExpanded():
                    self.Expand(_tree_section)
            self.check_selected(_tree_section, _section)

    def build_section_items(self, tree_section, section):
        """Build tree elements from section"""

        for _shape in section.design_place.get_all_shapes():
            _tree_shape = self.AppendItem(tree_section,
                _shape.__class__.__name__)
            self.SetPyData(_tree_shape, _shape)
            self.check_selected(_tree_shape, _shape)
