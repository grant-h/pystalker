import re
import glob
import logging
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from .xml_file import StalkerXmlFile

log = logging.getLogger(__name__)

class StringTableGroup:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.table = {}

    @lru_cache
    def lookup(self, key):
        for t in self.table.values():
            if key in t.entry:
                return t.entry[key]

    def walk(self):
        table_files = list(map(Path, sorted(glob.glob(str(self.base_path / "*.xml")))))

        for table_file in table_files:
            st = StringTableFile(table_file)
            try:
                st.parse()
                self.table[table_file] = st
            except ET.ParseError as e:
                log.warning("Failed to parse %s: %s", table_file, e)
                pass

class StringTableFile(StalkerXmlFile):

    def __init__(self, path):
        super().__init__(path)
        self.entry = {}

    def parse(self):
        tree = super().parse()
        root = tree.getroot()

        assert root.tag == "string_table"
        for st in root:
            assert st.tag == "string"
            st_id = st.attrib['id']

            text_ele = st[0]
            assert text_ele.tag == "text"

            value = text_ele.text
            self.entry[st_id] = value

    def __repr__(self):
        return "<StringTableFile %s, %d entries>" % (self.path, len(self.entry))
