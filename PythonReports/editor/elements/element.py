"""Base element type, can Listen properties and parse them from validators"""
"""
20-mar-2012 [kacah]    created

"""
from copy import copy

from ..propertiesgrid import PropertiesListener
from PythonReports import datatypes

"""...This is the only element in PythonReports templates
that has significant body text; (PythonReports Doc - Data)

"""
ELEMENTS_WITH_BODY = ["data"]

class XmlBody(datatypes.String):
    """Body of xml tag is also string.

    @note: is needed to identify class in datatypes_binding.py

    """


class PenTypeExtended(datatypes._Codes):
    """Normal enum for PenType - don't convert self into Dimension"""

    PEN_SIZES = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11",
        "12", "18", "24", "36", "48", ]

    VALUES = tuple(list(datatypes.PenType.VALUES) + PEN_SIZES)


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

    def check_validator_body(self, tag, attributes):
        """Check if given validator has xml body if true add __body attribute"""

        if tag in ELEMENTS_WITH_BODY:
            attributes[self.BODY_PROPERTY] = (XmlBody, "")

    def check_pentype(self, attributes):
        """Check if validator has PenType and change it to PenTypeExtended"""

        for (_attr_name, _attr) in attributes.items():
            if _attr[0] == datatypes.PenType:
                _new_attr = (PenTypeExtended, _attr[1])
                attributes[_attr_name] = _new_attr

    def _add_prop_one(self, val, val_type):
        """Add properties forom one validator"""

        _attributes = val.attributes.copy()
        self.check_validator_body(val.tag, _attributes)
        self.check_pentype(_attributes)
        self.add_attributes(val.tag, _attributes, val_type)

    def _add_prop_list(self, val_list, val_type):
        """Add properties from validators list"""

        for _validator in val_list:
            self._add_prop_one(_validator, val_type)

    def add_properties_from_validators(self):
        """Add all properties from validators to "properties" dictionary"""

        if self.main_val:
            self._add_prop_one(self.main_val, datatypes.Validator.ONE)
        self._add_prop_list(self.zero_or_one_val,
            datatypes.Validator.ZERO_OR_ONE)
        self._add_prop_list(self.one_val, datatypes.Validator.ONE)
        self._add_prop_list(self.unrestricted_val,
            datatypes.Validator.UNRESTRICTED)
