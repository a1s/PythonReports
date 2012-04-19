"""Loader for PythonReports xml template into editor"""
"""
18-apr-2012 [kacah]   created

"""
from PythonReports import datatypes
import PythonReports.template as te

from elements.element import *
from elements import design as ds
import utils

def load_template_file(template_file):
    """Load template file and return template"""

    return te.load(template_file)

def load_template(template, report):
    """Load template_file into given report"""

    load_report(template.getroot(), report)

def load_report(xml_report, report):
    """Load data from xml_report to report element"""

    load_main_validator(xml_report, report)

    _xml_layout = xml_report.find(te.Layout.tag)
    load_one_validator(_xml_layout, report, te.Layout)

    load_list_validator(xml_report, report, te.Parameter)
    load_list_validator(xml_report, report, te.Import)
    load_list_validator(xml_report, report, te.Variable)
    load_list_validator(xml_report, report, te.Font)
    load_list_validator(xml_report, report, te.Data)

    load_list_validator(_xml_layout, report, te.Style)

    load_main_headers(_xml_layout, report)
    load_columns(_xml_layout, report)
    load_groups(_xml_layout, report)

def load_main_headers(xml_layout, report):
    """Load headers and footers from xml layout to report element"""

    _xml_headers = [
        xml_layout.find(te.Header.tag), xml_layout.find(te.Title.tag),
        xml_layout.find(te.Summary.tag), xml_layout.find(te.Footer.tag)
    ]

    #1 - id in _xml_headers, 2 - attribute in report, 3 - object in report
    #4 - swap link
    HEADERS_LINK = [
        (0, "header", report.header_footer.get_first(), None),
        (1, "title", report.title_summary.get_first(), "swapheader"),
        (2, "summary", report.title_summary.get_second(), "swapfooter"),
        (3, "footer", report.header_footer.get_second(), None),
    ]

    for _header in HEADERS_LINK:
        _xml_section = _xml_headers[_header[0]]

        load_one_of_pair(_xml_section, report, _header[2], _header[1])

        if (_xml_section is not None) and _header[3]:
            report.set_value("headers", _header[3],
                datatypes.Boolean(_xml_section.get(_header[3])))

def load_columns(xml_layout, report):
    """Load data from xml_layout to columns element"""

    _xml_columns = xml_layout.find(te.Columns.tag)

    if _xml_columns is not None:
        load_one_validator(_xml_columns, report.columns, te.Columns)
        load_list_validator(_xml_columns, report.columns, te.Style)
        load_section_pair(_xml_columns, report.columns, ("header", "footer"))

    report.set_value(te.Columns.tag, report.EXISTANCE_PROPERTY,
        datatypes.Boolean(_xml_columns is not None))

def load_groups(xml_parent, report):
    """Load data from xml_layout to groups list"""

    #if there is a detail section finish loading groups
    _xml_detail = xml_parent.find("detail")
    if _xml_detail is not None:
        load_section(_xml_detail, report.detail)
        return

    _xml_group = xml_parent.find("group")
    if _xml_group is not None:
        load_group(_xml_group, report)
        load_groups(_xml_group, report)

def load_group(xml_group, group_parent):
    """Load one group to groups list"""

    _list_property_value = group_parent.get_value(group_parent.LIST_CATEGORY,
        te.Group.tag)

    _group_elmt = _list_property_value.add()
    load_one_validator(xml_group, _group_elmt, te.Group)

    _report_group = group_parent.groups[-1]

    load_list_validator(xml_group, _report_group, te.Style)
    load_section_pair(xml_group, _report_group, ("title", "summary"))

def load_section_pair(xml_elmnt, section_pair, pair_names):
    """Load header-footer or title-summary pair"""

    load_one_of_pair(xml_elmnt.find(pair_names[0]), section_pair,
        section_pair.get_first(), pair_names[0])
    load_one_of_pair(xml_elmnt.find(pair_names[1]), section_pair,
        section_pair.get_second(), pair_names[1])

def load_one_of_pair(xml_section, section_pair, report_section, section_name):
    """Load one of section pair sections"""

    _has_section = xml_section is not None

    section_pair.set_value("headers", section_name,
        datatypes.Boolean(_has_section))

    if _has_section:
        load_section(xml_section, report_section)

def load_section(xml_section, report_section):
    """Load data from xml section to report section"""

    load_subreports(xml_section, report_section)
    load_list_validator(xml_section, report_section, te.Style)
    load_list_validator(xml_section, report_section, te.Eject)

    _xml_box = xml_section.find(te.Box.tag)
    if _xml_box is not None:
        report_section.set_height(utils.dim_to_screen(_xml_box.get("height")))
    else:
        #TODO: adjust section to elements
        report_section.set_height(300)

    load_shapes(xml_section, report_section)

def load_subreports(xml_section, report_section):
    """Load subreports from xml section to report section"""

    _xml_subreports = xml_section.findall(te.Subreport.tag)
    _list_property_value = report_section.get_value(
        report_section.LIST_CATEGORY, te.Subreport.tag)

    for _xml_subreport in _xml_subreports:
        _elmt = _list_property_value.add()
        _subreport = report_section.subreports[-1]
        load_main_validator(_xml_subreport, _subreport)
        load_list_validator(_xml_subreport, _subreport, te.Arg)

def load_shapes(xml_section, report_section):
    """Load Fields, Rectangles, Lines, Images and Barcodes to section"""

    SHAPES_TYPES = [
        ("rectangle", ds.Rectangle), ("image", ds.Image),
        ("barcode", ds.Barcode), ("line", ds.Line), ("field", ds.Field), ]

    for _shape_type in SHAPES_TYPES:
        load_shape(xml_section, report_section, _shape_type)

def load_shape(xml_section, report_section, shape_type):
    """Load one type of shapes to section"""

    _xml_shapes = xml_section.findall(shape_type[0])
    _design_place = report_section.design_place

    for _xml_shape in _xml_shapes:
        _shape = shape_type[1](_design_place, 0, 0, False)
        _design_place.add_element(_shape)

        load_main_validator(_xml_shape, _shape)
        load_list_validator(_xml_shape, _shape, te.Style)

        _xml_box = _xml_shape.find(te.Box.tag)
        _xml_data = _xml_shape.find(te.Data.tag)
        if _xml_box is not None:
            load_one_validator(_xml_box, _shape, te.Box)

        if _xml_data is not None:
            _shape.set_value(te.Data.tag, _shape.EXISTANCE_PROPERTY,
                datatypes.Boolean(True))
            load_one_validator(_xml_data, _shape, te.Data)


def load_main_validator(xml_elmnt, report_elmnt):
    """Load all attributes from tree to report that are in main validator"""

    load_one_validator(xml_elmnt, report_elmnt, report_elmnt.main_val)

def fix_element_changed(element, elem_type):
    """Fix elements that in editor are represenped with ither type.
    
    @note For example PenType changed to PenTypeExtended
    
    """
    CHANGE_TABLE = {
        datatypes.PenType: PenTypeExtended,
    }

    if CHANGE_TABLE.has_key(elem_type):
        return CHANGE_TABLE[elem_type](element.__str__())
    else:
        return element

def load_one_validator(xml_elmnt, report_elmnt, validator):
    """Load all attributes from xml tree to report that are in validator"""

    for (_attr_name, (_type, _default)) in validator.attributes.items():
        _value = fix_element_changed(xml_elmnt.get(_attr_name), _type)
        report_elmnt.set_value(validator.tag, _attr_name, _value)

    if xml_elmnt.tag in ELEMENTS_WITH_BODY:
        report_elmnt.set_value(validator.tag, Element.BODY_PROPERTY,
            XmlBody(xml_elmnt.text))

def load_list_validator(xml_parent, report_parent, validator):
    """Load all list properties from xml tree to report element"""

    _xml_elements = xml_parent.findall(validator.tag)
    _list_property_value = report_parent.get_value(report_parent.LIST_CATEGORY,
        validator.tag)

    for _xml_elmnt in _xml_elements:
        _elmt = _list_property_value.add()
        load_one_validator(_xml_elmnt, _elmt, validator)
