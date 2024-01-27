import glob
import logging
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path, PureWindowsPath
from .xml_file import StalkerXmlFile


log = logging.getLogger(__name__)

class TextureDescriptionGroup:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.files = {}

    @lru_cache
    def lookup(self, key):
        for t in self.files.values():
            if key in t.entry:
                return t.entry[key]

    def walk(self):
        files = list(map(Path, sorted(glob.glob(str(self.base_path / "*.xml")))))

        for fname in files:
            obj = TextureDescriptionFile(fname)
            try:
                obj.parse()
                self.files[fname] = obj
            except ET.ParseError as e:
                log.warning("Failed to parse %s: %s", fname, e)
                pass

class TextureDescriptionFile(StalkerXmlFile):

    def __init__(self, path):
        super().__init__(path)
        self.entry = {}

    def get(self, key):
        return self.entry[key]

    def items(self):
        return self.entry.items()

    def parse(self):
        tree = super().parse()
        root = tree.getroot()

        assert root.tag == "w"

        for tfile in root:
            for tex in tfile:
                info = {'path': PureWindowsPath(tfile.attrib["name"])}
                tname = tex.attrib["id"]
                info.update(tex.attrib)
                self.entry[tname] = info

    def __repr__(self):
        return "<TextureDescriptionFile %s, %d entries>" % (self.path, len(self.entry))
