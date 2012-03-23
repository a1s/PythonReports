"""Base element type, can Listen properties and parse them from validators"""
"""
20-mar-2012 [kacah]   created

"""
from propertiesgrid import PropertiesListener

class Element(PropertiesListener):
    """Base class for all elements"""

    def __init__(self, prop_grid, main_val, single_val=[], multiple_val=[]):
        """Parameters explanation read in PythonReportsBinder 
        and PropertiesListener classes
        
        """

        PropertiesListener.__init__(self, prop_grid)

        self.main_val = main_val
        self.single_val = single_val
        self.multiple_val = multiple_val

        self.add_properties_from_validators()

    def add_properties_from_validators(self):
        """Add all properties from validators to "properties" dictionary"""

        self.add_attributes(self.main_val.tag, self.main_val.attributes)

        for _validator in self.single_val:
            self.add_attributes(_validator.tag, _validator.attributes)
