"""Classes for groups and columns"""
"""
30-mar-2012 [kacah]   created

"""

from section import Section

PAIR_TITLE_SUMMARY = 0
PAIR_HEADER_FOOTER = 1
PAIR_TITLES = [("title", "summary"), ("header", "footer")]

class SectionPair(object):
    """Pair of header/footer of title/summary elements"""

    def __init__(self, parent, prop_grid, width, p_id, prefix=""):
        """Create two section elements
        
        @param p_id: 0 - title, summary | 1 - header, footer
        @param prefix: string, prefix of titles
        
        """
        _titles = self.build_titles(prefix, p_id)
        self.first = Section(parent, prop_grid, _titles[0], width)
        self.second = Section(parent, prop_grid, _titles[1], width)

    def build_titles(self, prefix, p_id):
        """Build titles of pair by prefix and pair name id"""

        return (prefix + PAIR_TITLES[p_id][0], prefix + PAIR_TITLES[p_id][1])

    def set_visible(self, visible):
        """Set both pair elements visible or not"""
        self.first.set_visible(visible)
        self.second.set_visible(visible)

    def set_width(self, width):
        """Set width of both pair elements"""
        self.first.set_width(width)
        self.second.set_width(width)

    def get_first(self):
        """Get first section of pair"""
        return self.first

    def get_second(self):
        """Get second element of pair"""
        return self.second

class Columns(SectionPair):
    """PythonReports Columns element"""

    def __init__(self, parent, prop_grid, width):
        SectionPair.__init__(self, parent, prop_grid, width, PAIR_TITLE_SUMMARY,
            "Columns ")

    def count_width(self, width, number, gap):
        """Count columns width by columns number and gap"""

        return width / number - (number - 1) * gap

class Group(SectionPair):
    """PythonReports Group element"""

    def __init__(self, parent, prop_grid, width, group_id):
        SectionPair.__init__(self, parent, prop_grid, width, PAIR_HEADER_FOOTER,
            "Group ")

        self.group_id = group_id
        self.group_name = ""

    def destroy(self):
        """Destroy Header and footer containers"""

        self.first.Destroy()
        self.second.Destroy()

    def set_group_name(self, name):
        """Set name of group and rename sections"""

        self.group_name = name
        _titles = self.build_titles("Group '%s' " % name, PAIR_HEADER_FOOTER)
        self.first.set_title(_titles[0])
        self.second.set_title(_titles[1])

