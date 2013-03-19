"""Loader for PythonReports xml template into editor"""

from PythonReports import datatypes
import PythonReports.template as te
import wx

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

#1 - header tag, 2 - object in report, 3 - swap link
HEADERS_LINK = [
    (te.Header.tag, "report.header_footer.get_first()", None),
    (te.Footer.tag, "report.header_footer.get_second()", None),
    (te.Title.tag, "report.title_summary.get_first()", "swapheader"),
    (te.Summary.tag, "report.title_summary.get_second()", "swapfooter"),
]

def load_main_headers(xml_layout, report):
    """Load headers and footers from xml layout to report element"""

    for _header in HEADERS_LINK:
        _xml_section = xml_layout.find(_header[0])
        _found = (_xml_section is not None)
        report.set_value("headers", _header[0], datatypes.Boolean(_found))
        if _found:
            load_section(_xml_section, eval(_header[1]))
            if  _header[2]:
                report.set_value("headers", _header[2],
                    datatypes.Boolean(_xml_section.get(_header[2])))

def load_columns(xml_layout, report):
    """Load data from xml_layout to columns element"""

    _xml_columns = xml_layout.find(te.Columns.tag)

    if _xml_columns is not None:
        load_one_validator(_xml_columns, report.columns, te.Columns)
        load_list_validator(_xml_columns, report.columns, te.Style)
        load_section_pair(_xml_columns, report.columns,
            (te.Header.tag, te.Footer.tag))

    report.set_value(te.Columns.tag, report.EXISTANCE_PROPERTY,
        datatypes.Boolean(_xml_columns is not None))

def load_groups(xml_parent, report):
    """Load data from xml_layout to groups list. Load Detail section."""

    #if there is a detail section finish loading groups
    _xml_detail = xml_parent.find(te.Detail.tag)
    if _xml_detail is not None:
        load_section(_xml_detail, report.detail)
        return

    _xml_group = xml_parent.find(te.Group.tag)
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
    load_section_pair(xml_group, _report_group, (te.Title.tag, te.Summary.tag))

def load_section_pair(xml_elmnt, section_pair, pair_names):
    """Load header-footer or title-summary pair"""

    for (_name, _report_section) in zip(pair_names, section_pair.items()):
        _xml_section = xml_elmnt.find(_name)
        _found = (_xml_section is not None)
        section_pair.set_value("headers", _name, datatypes.Boolean(_found))
        if _found:
            load_section(_xml_section, _report_section)

def load_section(xml_section, report_section):
    """Load data from xml section to report section"""

    load_subreports(xml_section, report_section)
    load_list_validator(xml_section, report_section, te.Style)
    load_list_validator(xml_section, report_section, te.Eject)

    load_shapes(xml_section, report_section)

    _xml_box = xml_section.find(te.Box.tag)
    if _xml_box is not None:
        report_section.set_value("box", "height", _xml_box.get("height"))
    else:
        report_section.set_value("box", "height", datatypes.Dimension(-1))

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

SHAPES_LINK = {
    te.Rectangle.tag: ds.Rectangle,
    te.Image.tag: ds.Image,
    te.BarCode.tag: ds.Barcode,
    te.Line.tag: ds.Line,
    te.Field.tag: ds.Field,
}

def load_shapes(xml_section, report_section):
    """Load Fields, Rectangles, Lines, Images and Barcodes to section"""

    for _section_child in xml_section:
        if _section_child.tag in SHAPES_LINK.keys():
            load_shape(_section_child, report_section,
                SHAPES_LINK[_section_child.tag])

def load_shape(xml_shape, report_section, shape_class):
    """Load one shape from xml to section"""

    _design_place = report_section.design_place

    _shape = shape_class(_design_place, 0, 0, False)
    _design_place.add_element(_shape)

    load_main_validator(xml_shape, _shape)
    load_list_validator(xml_shape, _shape, te.Style)

    _xml_box = xml_shape.find(te.Box.tag)
    _xml_data = xml_shape.find(te.Data.tag)
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
    """Fix elements that in editor are represented with other type.

    @note: For example PenType changed to PenTypeExtended

    """
    CHANGE_TABLE = {
        datatypes.PenType: PenTypeExtended,
    }

    if CHANGE_TABLE.has_key(elem_type):
        return CHANGE_TABLE[elem_type](unicode(element))
    else:
        return element

def load_one_validator(xml_elmnt, report_elmnt, validator):
    """Load all attributes from xml tree to report that are in validator"""

    for (_attr_name, (_type, _default)) in validator.attributes.items():
        _value = fix_element_changed(xml_elmnt.get(_attr_name), _type)
        report_elmnt.set_value(validator.tag, _attr_name, _value)

    if validator.tag in ELEMENTS_WITH_BODY:
        report_elmnt.set_value(validator.tag, Element.BODY_PROPERTY,
            XmlBody(xml_elmnt.text.strip() if xml_elmnt.text else ""))

def load_list_validator(xml_parent, report_parent, validator):
    """Load all list properties from xml tree to report element"""

    _xml_elements = xml_parent.findall(validator.tag)
    _list_property_value = report_parent.get_value(report_parent.LIST_CATEGORY,
        validator.tag)

    for _xml_elmnt in _xml_elements:
        _elmt = _list_property_value.add()
        load_one_validator(_xml_elmnt, _elmt, validator)

# vim: set et sts=4 sw=4 :
