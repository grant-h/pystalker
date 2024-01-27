import logging
import glob
import re

from copy import deepcopy
from enum import Enum
from pathlib import Path, PureWindowsPath

log = logging.getLogger(__name__)

"""
The STALKER / OpenXRay engine's LTX file format is an enhanced Windows/DOS INI file.
The new file format includes additional features, such as INI
section inheritance and includes.
The OpenXRay implementation is here https://github.com/OpenXRay/xray-16/blob/master/src/xrCore/xr_ini.cpp

The STALKER Anomaly mod forks the OpenXRay engine and changes the LTX parser, enabling include file globbing (e.g. "base_*.ltx"), amongst other features. See https://bitbucket.org/anomalymod/xray-monolith/src/master/src/xrCore/Xr_ini.cpp
"""

class LTXParseError(Exception):
    pass

class LTXFile:
    def __init__(self, path):
        self.path = path
        self.tree = None

    def read(self):
        data = open(self.path, 'rb').read()

        try:
            # utf-8-sig will correctly handle BOM/no-BOM encodings
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return data.decode("latin1")

    def __repr__(self):
        return "<LTXFile %s>" % (self.path)

class LTXSection:
    def __init__(self, name, parents=[]):
        self.name = name
        self.parents = parents
        self.keys = {}
        self.defined_in = None

    def set_declaration_info(self, ltx_file):
        self.defined_in = ltx_file

    def __len__(self):
        return len(self.keys)

    def set(self, key, value=None):
        self.keys[key] = value

    def get_key_hier(self, key):
        values = []
        value = self.get(key)

        # No parents have the value if we dont
        if value is None:
            return []

        values.append((value, self))

        for sec in self.parents[::-1]:
            value = sec.get_key_hier(key)

            if len(value):
                values += value

        return values

    def has(self, key):
        return self.get(key) is not None

    def get_all(self):
        values = {}

        for parent in self.parents:
            pvalues = parent.get_all()
            # later parents override values
            values.update(pvalues)

        # current section overrides parents
        values.update(self.keys)

        return deepcopy(values)

    def get(self, key, default=None):
        if key in self.keys:
            value = self.keys.get(key, default)
            if isinstance(value, list):
                value = list(value)
            return value

        # Later parents take precedence
        for parent in self.parents[::-1]:
            value = parent.get(key, None)

            if value is not None:
                if isinstance(value, list):
                    # make a copy of the list as we don't want direct object modification
                    value = list(value)

                return value

        return default

    def get_list(self, key):
        val = self.get(key, [])
        if isinstance(val, str):
            val = [val]
        elif val is None:
            val = []

        return val

    def get_iter(self, key):
        for i in self.get_list(key):
            yield i

    def __repr__(self):
        return "<LTXSection %s, parents=%s, keys=%d, file=%s>" % \
                (self.name, len(self.parents), len(self), self.defined_in.path.name)

class LTXFileRoot:
    def __init__(self, ltx_root_path):
        self.ltx_root = LTXFile(ltx_root_path)
        self.section = {}

    def get(self, name):
        return self.section[name]

    def parse(self):
        # Build the LTX parse tree
        tree = parse_ltx(self.ltx_root.path)

        # Walk the tree, building sections in-order
        self._build(self.ltx_root, tree)

    def _build(self, ltx_file, tree):
        cur_section = None

        for entry in tree:
            ty = entry[0]
            values = entry[1:]

            if ty == "INCLUDE":
                inc_ltx, inc_ltx_tree = values
                self._build(inc_ltx, inc_ltx_tree)
            elif ty == "SECTION":
                name, parents = values
                if name in self.section:
                    log.warning("Overwriting section %s", name)

                sec_parents = []
                for parent in parents:
                    if parent not in self.section:
                        raise LTXParseError("Missing section %s" % (parent))

                    sec_parents.append(self.section[parent])

                cur_section = LTXSection(name, sec_parents)
                cur_section.set_declaration_info(ltx_file)

                self.section[name] = cur_section
            elif ty == "ASSIGN":
                key, assign_values = values

                if key is None:
                    key = len(cur_section)

                if len(assign_values) == 1:
                    assign_values = assign_values[0]
                elif len(assign_values) == 0:
                    assign_values = None

                cur_section.set(key, assign_values)
            else:
                assert 0, "Unhandled type %s" % (ty)

class LTXToken(Enum):
    INHERIT = re.compile(r'[:]')
    INCLUDE = re.compile(r'#include')
    COMMA = re.compile(r'[,]')
    ASSIGN = re.compile(r'[=]')
    HEADER_OPEN = re.compile(r'[\[]')
    HEADER_CLOSE = re.compile(r'[\]]')

    IDENTIFIER = re.compile(r'[^\[\]"=\n\r\t ,;:{}][^\[\]"=\n\r\t ,;{}]*')
    QUOTED_STRING = re.compile(r'"[^\n\r"]*"')
    CONSTRAINT = re.compile(r'\{[^\n\r}]*\}')
    EVAL = re.compile(r'%[^\n\r%]*%')
    EOL = re.compile(r'(\r\n|\n)')

    @classmethod
    def get_match(cls, stream):
        choice = None

        for k, v in cls.__members__.items():
            m = v.value.match(stream)
            if m:
                string = m.group(0)
                if choice:
                    if len(string) > len(choice[1]):
                        choice = (k, string)
                else:
                    choice = (k, string)

        return choice

class LTXParseContext:
    WHITESPACE = re.compile(r'[\n\r\t ]+')
    SPACING = re.compile(r'[\t ]+')
    COMMENT = re.compile(r'(;|--|//)[^\r\n]*')

    def __init__(self, data):
        self.data = data
        self.offset = 0
        self.line = 0
        self.column = 0

    def get_data(self):
        return self.data[self.offset:]

    def advance(self, amt):
        skip_data = self.data[self.offset:self.offset+amt]
        newlines = skip_data.count("\n")

        if newlines > 0:
            self.line += newlines
            self.column = len(skip_data) - (skip_data.rfind("\n") + 1) - 1
        else:
            self.column += amt

        self.offset += amt

    def get_match(self):
        data = self.get_data()

        if len(data) == 0:
            return ("EOF", "")

        m = LTXToken.get_match(data)
        if m is None:
            self.error("Unable to match token '%s'", data[:1])

        return m

    def skip_ws(self):
        while True:
            data = self.get_data()

            m = LTXParseContext.SPACING.match(data)
            if m:
                self.advance(len(m.group(0)))
                continue

            m = LTXParseContext.COMMENT.match(data)
            if m:
                self.advance(len(m.group(0)))
                continue

            break

    def error(self, message, *args):
        raise LTXParseError(message % tuple(args))

def parse_ltx(top_level_ltx):
    log.info("Parsing %s", top_level_ltx)
    ltx_top = LTXFile(Path(top_level_ltx))
    ltx_data = ltx_top.read()

    ctx = LTXParseContext(ltx_data)

    section_name = None

    tree = []

    while ctx.offset < len(ltx_data):
        ctx.skip_ws()
        tok, v = ctx.get_match()

        if 0:
            data = ctx.get_data()
            line = data[:data.find("\n")]

            print("LINE '%s'" % (line.replace("\t", " ").strip()))

        if tok == "EOL":
            ctx.advance(len(v))
            ctx.skip_ws()
            continue
        elif tok == "INCLUDE":
            ctx.advance(len(v))
            ctx.skip_ws()

            tok, v = ctx.get_match()

            if tok != "QUOTED_STRING":
                ctx.error("Expected string as include argument")

            ctx.advance(len(v))

            # Normalize windows paths
            bare_path = v[1:-1]
            include_value = PureWindowsPath(bare_path)
            include_path = ltx_top.path.parent / include_value

            if bare_path.find("*") != -1:
                includes = sorted(map(lambda x: Path(x), glob.glob(str(include_path))))
            else:
                includes = [include_path]

            for include in includes:
                if include.exists():
                    inc_ltx = LTXFile(include)
                    inc_ltx_tree = parse_ltx(include)
                    tree.append(("INCLUDE", inc_ltx, inc_ltx_tree))
                else:
                    log.warning("Missing include %s", include)

        elif tok == "HEADER_OPEN":
            ctx.advance(len(v))
            ctx.skip_ws()

            tok, v = ctx.get_match()
            if tok != "IDENTIFIER":
                ctx.error("Expected section identifier after section start [")

            section_name = v
            section_parents = []

            ctx.advance(len(v))
            ctx.skip_ws()
            tok, v = ctx.get_match()

            if tok != "HEADER_CLOSE":
                ctx.error("Expected section close ] after identifier")

            ctx.advance(len(v))
            ctx.skip_ws()
            tok, v = ctx.get_match()

            if tok == "INHERIT":
                ctx.advance(len(v))
                ctx.skip_ws()

                while True:
                    tok, v = ctx.get_match()
                    ctx.advance(len(v))
                    ctx.skip_ws()

                    if tok == "COMMA":
                        pass
                    elif tok == "IDENTIFIER":
                        section_parents.append(v)
                    elif tok == "EOL" or tok == "EOF":
                        break

            tree.append(("SECTION", section_name, section_parents))
        elif tok == "IDENTIFIER":
            if section_name is None:
                ctx.error("Identifier out of section")

            key = v
            assign_values = []

            ctx.advance(len(v))
            ctx.skip_ws()
            tok, v = ctx.get_match()

            if tok == "ASSIGN":
                ctx.advance(len(v))
                ctx.skip_ws()

            elif tok == "EOL":
                # bare identifier (section is a array of items, not a dict)
                ctx.advance(len(v))
                ctx.skip_ws()

                # key was in-fact a value assignment to an array index (determined later)
                assign_values.append(key)
                tree.append(("ASSIGN", None, assign_values))
                continue

            is_csv = False

            while True:
                tok, v = ctx.get_match()
                ctx.advance(len(v))
                ctx.skip_ws()

                # null assignment
                if tok == "EOL" or tok == "EOF":
                    break
                elif tok == "QUOTED_STRING":
                    assign_values.append(v[1:-1])
                elif tok == "IDENTIFIER":
                    assign_values.append(v)
                elif tok == "COMMA":
                    is_csv = True
                elif tok == "CONSTRAINT" or tok == "EVAL":
                    # TODO
                    pass
                else:
                    assert 0, tok

            if len(assign_values) > 1 and not is_csv and key != "precondition_parameter":
                log.warning("Coalescing whitespace in key %s value %s. Use quotes",
                        key, assign_values)

                assign_values = ["".join(assign_values)]

            tree.append(("ASSIGN", key, assign_values))
        elif tok == "EOF":
            break
        else:
            ctx.error("Unhandled token %s", tok)

    return tree
