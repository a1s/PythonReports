"""Bind PythonReports validators to editor"""
"""
20-mar-2012 [kacah]   created

"""
class PythonReportsBinder(object):
    def __init__(self, main_val, single_val=[], multiple_val=[]):
        """Add validators to object
        
        @param main_val: validator for element itself
        @param single_val: validators list for ONE or ZERO_OR_ONE elements
        @param multiple_val: validators list for UNRESTRICTED elements
        
        """
        self.main_val = main_val
        self.single_val = single_val
        self.multiple_val = multiple_val
