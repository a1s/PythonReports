"""Test all unittests"""
"""
19-may-2012 [kacah] created

"""
import unittest


def load_test_system(loader, main_suite):
    """Load tests from test_system"""

    import test_system

    _utils_suite = unittest.TestSuite(
        loader.loadTestsFromTestCase(test_system.TestUtils))
    _templates_suite = unittest.TestSuite(
        loader.loadTestsFromTestCase(test_system.TestTemplates))

    main_suite.addTest(_utils_suite)
    main_suite.addTest(_templates_suite)
    
def load_test_properties(loader, main_suite):
    """Load test from test_properties"""

    import test_properties

    _listener_suite = unittest.TestSuite(
        loader.loadTestsFromTestCase(test_properties.TestPropertiesListener))
    _grid_suite = unittest.TestSuite(
        loader.loadTestsFromTestCase(test_properties.TestPropertiesGrid))

    main_suite.addTest(_listener_suite)
    main_suite.addTest(_grid_suite)

def load_test_report(loader, main_suite):
    """Load test from test_report"""

    import test_report

    _report_suite = unittest.TestSuite(
        loader.loadTestsFromTestCase(test_report.TestReport))

    main_suite.addTest(_report_suite)
    
def load_test_section(loader, main_suite):
    """Load test from test_section"""

    import test_section

    _section_suite = unittest.TestSuite(
        loader.loadTestsFromTestCase(test_section.TestSection))

    main_suite.addTest(_section_suite)

def load_tests(loader, tests, pattern):
    """Load all tests"""

    _main_suite = unittest.TestSuite()
    load_test_system(loader, _main_suite)
    load_test_properties(loader, _main_suite)
    load_test_report(loader, _main_suite)
    load_test_section(loader, _main_suite)
    return _main_suite

if __name__ == "__main__":
    unittest.main()
