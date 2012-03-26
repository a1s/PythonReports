"""Base element type, can Listen properties and parse them from validators"""
"""
20-mar-2012 [kacah]   created

"""
from propertiesgrid import PropertiesListener
import PythonReports.datatypes as datatypes

class Element(PropertiesListener):
    """Base class for all elements"""

    def __init__(self, prop_grid, main_val,
        zero_or_one_val=[], one_val=[], unrestricted_val=[]):
        """Parameter prop_grid explanation read in PropertiesListener classes
        
        @param *_val: validators from PythonReports
        
        """
        PropertiesListener.__init__(self, prop_grid)

        self.main_val = main_val
        self.zero_or_one_val = zero_or_one_val
        self.one_val = one_val
        self.unrestricted_val = unrestricted_val

        self.add_properties_from_validators()

    def add_properties_from_validators(self):
        """Add all properties from validators to "properties" dictionary"""

        self.add_attributes(self.main_val.tag, self.main_val.attributes,
            datatypes.Validator.ONE)

        for _validator in self.zero_or_one_val:
            self.add_attributes(_validator.tag, _validator.attributes,
                datatypes.Validator.ZERO_OR_ONE)

        for _validator in self.one_val:
            self.add_attributes(_validator.tag, _validator.attributes,
                datatypes.Validator.ONE)

        for _validator in self.unrestricted_val:
            self.add_attributes(_validator.tag, _validator.attributes,
                datatypes.Validator.UNRESTRICTED)
