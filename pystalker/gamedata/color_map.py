import xml.etree.ElementTree as ET

def parse_color_map(path):
    tree = ET.parse(path)
    root = tree.getroot()

    cmap = {}
    for c in root:
        cmap[c.attrib['name']] = (
            c.attrib.get('r', 0),
            c.attrib.get('g', 0),
            c.attrib.get('b', 0),
            c.attrib.get('a', 255)
        )

    return cmap
