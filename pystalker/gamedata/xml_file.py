import re
import xml.etree.ElementTree as ET
import logging
from io import BytesIO

log = logging.getLogger(__name__)

class StalkerXmlFile:
    COMMENT = re.compile(rb'<!--.*?-->', re.MULTILINE | re.DOTALL)
    BARE_AMP = re.compile(rb'&')

    def __init__(self, path):
        self.path = path

    def read(self):
        return open(self.path, 'rb').read()

        try:
            # utf-8-sig will correctly handle BOM/no-BOM encodings
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return data.decode("latin1")

    def parse(self):
        log.info("Parsing %s", self.path)

        # Strip comments as they are not XML standard compliant...
        data = BytesIO(
            self.BARE_AMP.sub(
                b'&amp;',
                self.COMMENT.sub(b'', self.read())
            )
        )

        return ET.parse(data)

    def __repr__(self):
        return "<StalkerXmlFile %s>" % (self.path)
