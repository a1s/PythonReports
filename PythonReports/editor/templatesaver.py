"""Saver for PythonReports xml template from editor"""

try:
    # preferred to pure python because it's faster
    import cElementTree as xmllib
except ImportError:
    try:
        # preferred to batteries just because you bothered to install it
        import elementtree.ElementTree as xmllib
    except ImportError:
        # pylint: disable-msg=E0611
        # E0611: No name 'etree' in module 'xml' - true for python <2.5
        # ... pylint still reports this error
        # last resort; should always success in python2.5 and newer
        import xml.etree.ElementTree as xmllib
import xml.dom.minidom as minidom

from PythonReports import datatypes
import PythonReports.template as te

from elements.element import *
import utils


FILE_ENCODING = "utf-8"

def write_text_node(writer, node, newl):
    """No indents for text node. Just single line."""

    writer.write(">")
    node.childNodes[0].writexml(writer, "", "", "")
    writer.write("</%s>%s" % (node.tagName, newl))

def writexml_patch(self, writer, indent="", addindent="", newl=""):
    """Fix bug in minidom, when output of text nodes was indented too"""

    writer.write(indent + "<" + self.tagName)

    attrs = self._get_attributes()
    a_names = attrs.keys()
    a_names.sort()

    for a_name in a_names:
        writer.write(" %s=\"" % a_name)
        minidom._write_data(writer, attrs[a_name].value)
        writer.write("\"")
    if self.childNodes:
        #check if this node contains only TEXT_NODE, then print with no indents
        if len(self.childNodes) == 1 \
          and self.childNodes[0].nodeType == minidom.Node.TEXT_NODE:
            write_text_node(writer, self, newl)
            return
        writer.write(">%s" % (newl))
        for node in self.childNodes:
            node.writexml(writer, indent + addindent, addindent, newl)
        writer.write("%s</%s>%s" % (indent, self.tagName, newl))
    else:
        writer.write("/>%s" % (newl))

#MonkeyPatch: replace minidom's function with fixed
#TODO: implement normal ElementTree saving, or use another library
minidom.Element.writexml = writexml_patch

def save_template_file(report, file_name):
    """Save report to given filename as xml template. Path must exist."""
    _xml_template = create_xml_template(report)
    _xml_template.write(file_name)
    # FIXME: remaining lines and supporting functions seem to be unneeded
    return
    _simple_string = xmllib.tostring(_xml_template.getroot(),
        encoding=FILE_ENCODING)

    _pretty_string = minidom.parseString(_simple_string).toprettyxml()

    with open(file_name, "w") as _file:
        _file.write(_pretty_string.encode(FILE_ENCODING))

def create_xml_template(report):
    """Return full xml tree created from given report element"""

    _xml_report = xmllib.Element(te.Report.tag)
    save_xml_report(report, _xml_report)
    return datatypes.ElementTree(te.Report, _xml_report)

def save_xml_report(report, xml_report):
    """Save data from reports to xml_report element"""

    save_validator(report, xml_report, te.Report)

    save_list_validator(report, xml_report, te.Font)
    save_list_validator(report, xml_report, te.Parameter)
    save_list_validator(report, xml_report, te.Variable)
    save_list_validator(report, xml_report, te.Import)
    save_list_validator(report, xml_report, te.Data)

    _xml_layout = xmllib.SubElement(xml_report, te.Layout.tag)
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
        _xml_columns = xmllib.SubElement(xml_layout, te.Columns.tag)

        save_validator(report.columns, _xml_columns, te.Columns)
        save_list_validator(report.columns, _xml_columns, te.Style)
        save_section_pair(report.columns, _xml_columns,
            (te.Header.tag, te.Footer.tag))

def save_groups(report, xml_layout):
    """Save data from report groups to xmllib. Save detail section."""

    _last_xml_parent = xml_layout
    for _group in report.groups:
        _xml_group = xmllib.SubElement(_last_xml_parent, te.Group.tag)
        save_group(_group, _xml_group)
        _last_xml_parent = _xml_group

    _xml_detail = xmllib.SubElement(_last_xml_parent, te.Detail.tag)
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
        _xml_section = xmllib.SubElement(xml_parent, xml_section_tag)
        save_section(report_section, _xml_section)
        return _xml_section

def save_section(report_section, xml_section):
    """Save all data from report section to xml section element"""

    _height = report_section.get_value("box", "height")
    if _height > -1:
        _xml_box = xmllib.SubElement(xml_section, te.Box.tag)
        _xml_box.set("height", unicode(_height))

    save_subreports(report_section, xml_section)
    save_list_validator(report_section, xml_section, te.Style)
    save_list_validator(report_section, xml_section, te.Eject)

    save_shapes(report_section, xml_section)

def save_shapes(report_section, xml_section):
    """Save all shapes from report section to xml section"""

    _design_place = report_section.design_place

    for _shape in _design_place.get_all_shapes():
        save_shape(report_section, xml_section, _shape)

def save_shape(report_section, xml_section, shape):
    """Load one type of shapes from report to xml section"""

    _xml_shape = xmllib.SubElement(xml_section, shape.main_val.tag)

    save_validator(shape, _xml_shape, shape.main_val)
    _xml_box = xmllib.SubElement(_xml_shape, te.Box.tag)
    save_validator(shape, _xml_box, te.Box)
    save_list_validator(shape, _xml_shape, te.Style)

    if shape.has_value(te.Data.tag, shape.EXISTANCE_PROPERTY) and \
    shape.get_value(te.Data.tag, shape.EXISTANCE_PROPERTY):
        _xml_data = xmllib.SubElement(_xml_shape, te.Data.tag)
        save_validator(shape, _xml_data, te.Data)

def save_subreports(report_section, xml_section):
    """Save all subreport data from section to xml"""

    for _subreport in report_section.subreports:
        _xml_subreport = xmllib.SubElement(xml_section, te.Subreport.tag)

        save_validator(_subreport, _xml_subreport, te.Subreport)
        save_list_validator(_subreport, _xml_subreport, te.Arg)

def save_list_validator(report_element, xml_elemnt, validator):
    """Save list property from report like SubElements in xml_elmnt"""

    _list_property_value = report_element.get_value(
        report_element.LIST_CATEGORY, validator.tag)

    for _list_elmnt in _list_property_value.get_all():
        _xml_sub_elmnt = xmllib.SubElement(xml_elemnt, validator.tag)
        save_validator(_list_elmnt, _xml_sub_elmnt, validator)

def save_validator(report_elmnt, xml_elmnt, validator):
    """Save validator's attributes from report props to xml_elmnt attributes"""

    for (_attr_name, _attr_params) in validator.attributes.items():
        _value = report_elmnt.get_value(validator.tag, _attr_name)
        #if value is not default value - don't need to save defaults
        if not _value == _attr_params[1]:
            xml_elmnt.set(_attr_name, unicode(_value))

    if validator.tag in ELEMENTS_WITH_BODY:
        xml_elmnt.text = report_elmnt.get_value(validator.tag,
            Element.BODY_PROPERTY)
