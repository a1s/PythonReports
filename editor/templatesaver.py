"""Saver for PythonReports xml template from editor"""
"""
20-apr-2012 [kacah]   created

"""
try:
    # preferred to pure python because it's faster
    import cElementTree as xml
except ImportError:
    try:
        # preferred to batteries just because you bothered to install it
        import elementtree.ElementTree as xml
    except ImportError:
        # pylint: disable-msg=E0611
        # E0611: No name 'etree' in module 'xml' - true for python <2.5
        # ... pylint still reports this error
        # last resort; should always success in python2.5 and newer
        import xml.etree.ElementTree as xml
from xml.dom.minidom import parseString

from PythonReports import datatypes
import PythonReports.template as te

from elements.element import *
import utils


FILE_ENCODING = "utf-8"

def save_template_file(report, file_name):
    """Save report to given filename as xml template. Path must exist."""

    _xml_template = create_xml_template(report)

    _simple_string = xml.tostring(_xml_template,
        encoding=FILE_ENCODING)
    _pretty_string = parseString(_simple_string).toprettyxml()

    with open(file_name, "w") as _file:
        _file.write(_pretty_string)

def create_xml_template(report):
    """Return full xml tree created from given report element"""

    _xml_report = xml.Element(te.Report.tag)
    save_xml_report(report, _xml_report)
    return _xml_report

def save_xml_report(report, xml_report):
    """Save data from reports to xml_report element"""

    save_validator(report, xml_report, te.Report)

    save_list_validator(report, xml_report, te.Font)
    save_list_validator(report, xml_report, te.Parameter)
    save_list_validator(report, xml_report, te.Variable)
    save_list_validator(report, xml_report, te.Import)
    save_list_validator(report, xml_report, te.Data)

    _xml_layout = xml.SubElement(xml_report, te.Layout.tag)
    save_validator(report, _xml_layout, te.Layout)
    save_list_validator(report, _xml_layout, te.Style)

    save_main_headers(report, _xml_layout)
    save_columns(report, _xml_layout)
    save_groups(report, _xml_layout)

def save_main_headers(report, xml_layout):
    """Save headers and footers from report layout to xml layout element"""

    from templateloader import HEADERS_LINK

    for _header in HEADERS_LINK:
        _xml_section = \
            save_one_of_pair(eval(_header[1]), report, xml_layout, _header[0])

        #if has section and has swap flag and shap flag is set to True 
        if _xml_section is not None and _header[2] \
        and report.get_value("headers", _header[2]):
            _xml_section.set(_header[2], "True")

def save_columns(report, xml_layout):
    """Save data from report columns to xml"""

    _xml_columns = xml_layout.find(te.Columns.tag)

    if report.get_value(te.Columns.tag, report.EXISTANCE_PROPERTY):
        _xml_columns = xml.SubElement(xml_layout, te.Columns.tag)

        save_validator(report.columns, _xml_columns, te.Columns)
        save_list_validator(report.columns, _xml_columns, te.Style)
        save_section_pair(report.columns, _xml_columns,
            (te.Header.tag, te.Footer.tag))

def save_groups(report, xml_layout):
    """Save data from report groups to xml. Save detail section."""

    _last_xml_parent = xml_layout
    for _group in report.groups:
        _xml_group = xml.SubElement(_last_xml_parent, te.Group.tag)
        save_group(_group, _xml_group)
        _last_xml_parent = _xml_group

    _xml_detail = xml.SubElement(_last_xml_parent, te.Detail.tag)
    save_section(report.detail, _xml_detail)

def save_group(report_group, xml_group):
    """Save group data into xml_group"""

    save_validator(report_group, xml_group, te.Group)
    save_list_validator(report_group, xml_group, te.Style)
    save_section_pair(report_group, xml_group, (te.Title.tag, te.Summary.tag))

def save_section_pair(section_pair, xml_elmnt, pair_names):
    """Save header-footer or title-summary pair"""

    save_one_of_pair(section_pair.get_first(), section_pair, xml_elmnt,
        pair_names[0])
    save_one_of_pair(section_pair.get_second(), section_pair, xml_elmnt,
        pair_names[1])

def save_one_of_pair(report_section, section_pair, xml_parent, xml_section_tag):
    """Save report section to xml section as part of header/footer pair
    
    @return: created xml_section or None
    
    """
    if section_pair.get_value("headers", xml_section_tag):
        _xml_section = xml.SubElement(xml_parent, xml_section_tag)
        save_section(report_section, _xml_section)
        return _xml_section

def save_section(report_section, xml_section):
    """Save all data from report section to xml section element"""

    _xml_box = xml.SubElement(xml_section, te.Box.tag)
    _height = utils.screen_to_dim(report_section.get_height())
    _xml_box.set("height", str(_height))

    save_subreports(report_section, xml_section)
    save_list_validator(report_section, xml_section, te.Style)
    save_list_validator(report_section, xml_section, te.Eject)

    save_shapes(report_section, xml_section)

def save_shapes(report_section, xml_section):
    """Save all shapes from report section to xml section"""

    from templateloader import SHAPES_LINK

    for _shape_type in SHAPES_LINK:
        save_shape_type(report_section, xml_section, _shape_type)

def save_shape_type(report_section, xml_section, shape_type):
    """Load one type of shapes from report to xml section"""
    _design_place = report_section.design_place

    for _shape in _design_place.elements[shape_type[1]]:
        _xml_shape = xml.SubElement(xml_section, shape_type[0].tag)

        save_validator(_shape, _xml_shape, shape_type[0])
        _xml_box = xml.SubElement(_xml_shape, te.Box.tag)
        save_validator(_shape, _xml_box, te.Box)
        save_list_validator(_shape, _xml_shape, te.Style)

        if _shape.has_value(te.Data.tag, _shape.EXISTANCE_PROPERTY) and \
        _shape.get_value(te.Data.tag, _shape.EXISTANCE_PROPERTY):
            _xml_data = xml.SubElement(_xml_shape, te.Data.tag)
            save_validator(_shape, _xml_data, te.Data)

def save_subreports(report_section, xml_section):
    """Save all subreport data from section to xml"""

    for _subreport in report_section.subreports:
        _xml_subreport = xml.SubElement(xml_section, te.Subreport.tag)

        save_validator(_subreport, _xml_subreport, te.Subreport)
        save_list_validator(_subreport, _xml_subreport, te.Arg)

def save_list_validator(report_element, xml_elemnt, validator):
    """Save list property from report like SubElements in xml_elmnt"""

    _list_property_value = report_element.get_value(
        report_element.LIST_CATEGORY, validator.tag)

    for _list_elmnt in _list_property_value.get_all():
        _xml_sub_elmnt = xml.SubElement(xml_elemnt, validator.tag)
        save_validator(_list_elmnt, _xml_sub_elmnt, validator)

def save_validator(report_elmnt, xml_elmnt, validator):
    """Save validator's attributes from report props to xml_elmnt attributes"""

    for (_attr_name, _attr_params) in validator.attributes.items():
        _value = report_elmnt.get_value(validator.tag, _attr_name)
        #if value is not default value - don't need to save defaults
        if not _value == _attr_params[1]:
            xml_elmnt.set(_attr_name, str(_value))

    if validator.tag in ELEMENTS_WITH_BODY:
        xml_elmnt.text = report_elmnt.get_value(validator.tag,
            Element.BODY_PROPERTY)
