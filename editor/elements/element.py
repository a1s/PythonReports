"""Base element type, can Listen properties and parse them from validators"""
"""
20-mar-2012 [kacah]    created

"""
from propertiesgrid import PropertiesListener
from PythonReports import datatypes

"""...This is the only element in PythonReports templates 
that has significant body text; (PythonReports Doc - Data)

"""
ELEMENTS_WITH_BODY = ["data"]

class XmlBody(object):
    """Just contains body of xml tag - one string"""
    def __init__(self, data):
        self.data = data

class Element(PropertiesListener):
    """Base class for all elements"""

    def __init__(self, main_val=None,
        zero_or_one_val=[], one_val=[], unrestricted_val=[]):
        """@param *_val: validators from PythonReports"""

        PropertiesListener.__init__(self)

        self.main_val = main_val
        self.zero_or_one_val = zero_or_one_val
        self.one_val = one_val
        self.unrestricted_val = unrestricted_val

        self.add_properties_from_validators()

    BODY_PROPERTY = "__body"

    def check_validator_body(self, validator):
        """Check if given validator has xml body if true add __body attribute"""
        if validator.tag in ELEMENTS_WITH_BODY:
            validator.attributes[self.BODY_PROPERTY] = (XmlBody, "")

    def __add_prop_one(self, val, val_type):
        """Add properties form one validator"""
        self.check_validator_body(val)
        self.add_attributes(val.tag, val.attributes, val_type)

    def __add_prop_list(self, val_list, val_type):
        """Add properties form validators list"""
        for _validator in val_list:
            self.__add_prop_one(_validator, val_type)

    def add_properties_from_validators(self):
        """Add all properties from validators to "properties" dictionary"""

        if self.main_val:
            self.__add_prop_one(self.main_val, datatypes.Validator.ONE)
        self.__add_prop_list(self.zero_or_one_val,
            datatypes.Validator.ZERO_OR_ONE)
        self.__add_prop_list(self.one_val, datatypes.Validator.ONE)
        self.__add_prop_list(self.unrestricted_val,
            datatypes.Validator.UNRESTRICTED)
