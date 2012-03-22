"""Base element type, can Listen properties and parse them from validators"""
"""
20-mar-2012 [kacah]   created

"""
from pythonreports_binding import PythonReportsBinder
from propertiesgrid import PropertiesListener

class Element(PythonReportsBinder, PropertiesListener):
    """Base class for all elements"""

    def __init__(self, prop_grid, main_val, single_val=[], multiple_val=[]):
        """Parameters explanation read in PythonReportsBinder 
        and PropertiesListener classes
        
        """

        PythonReportsBinder.__init__(self, main_val, single_val, multiple_val)
        PropertiesListener.__init__(self, prop_grid)

        self.update_validators_to_properties()

    def update_validators_to_properties(self):
        """Add all properties from validators to "properties" dictionary"""

        self.update_attributes(self.main_val.tag, self.main_val.attributes)

        for _validator in self.single_val:
            self.update_attributes(_validator.tag, _validator.attributes)
