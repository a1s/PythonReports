"""Visual design elements, that can be placed in section"""
"""
03-apr-2012 [kacah]    created, added Subreport

"""
import PythonReports.template as te
import wx
import wx.lib.buttons as wxbtns

from container import HeaderButton
from elements.element import Element

SUBREPORT_MAIN = te.Subreport
SUBREPORT_UNRESTRICTED = [te.Arg]

class Subreport(wxbtns.GenButton, Element):
    """PythonReports subreport element"""

    SUBREPORT_HEIGHT = 20

    def __init__(self, parent, prop_grid, width, subreport_id, section):
        wxbtns.GenButton.__init__(self, parent, wx.ID_ANY, "Subreport",
            size=(1, self.SUBREPORT_HEIGHT))
        Element.__init__(self, prop_grid, SUBREPORT_MAIN,
            unrestricted_val=SUBREPORT_UNRESTRICTED)

        self.id = subreport_id
        self.section = section

        self.SetForegroundColour("white")
        self.SetBackgroundColour("grey")

        self.Bind(wx.EVT_SET_FOCUS, self.OnSelected)

    def destroy(self):
        """Destroy self"""
        self.Destroy()

    def set_title(self, title):
        """Set title of element"""
        self.SetLabel(title)

    def get_sequence(self):
        """Get seq value of Subreport"""
        return self.get_value("subreport", "seq")

    def update_name(self):
        """Update subreport name from properties"""

        _name = self.get_value("subreport", "template")
        _name = "Subreport '%s'" % _name
        self.set_title(_name)

    def after_property_changed(self, category, attribute):
        """Overrided from PropertiesListener"""

        if category == "subreport":
            self.update_name()
            self.section.synchronize_subreport(self)
