#!/usr/bin/env python3
import re
import sys
import logging
import json
import argparse
import readline

from pathlib import Path
from fnmatch import fnmatch

from pystalker.gamedata import StalkerGameData

log = logging.getLogger(__name__)

class CompletionState:
    MAX_COMPLETION = 100

    def __init__(self, ltx, st):
        self.ltx = ltx
        self.st = st
        self.top_level = list(ltx.section.keys())
        self._cached_lookup = None
        self._all_keys = True

    def get_section_keys(self, sect):
        if sect not in self.ltx.section:
            return []

        if self._all_keys:
            keys = self.ltx.section[sect].get_all().keys()
        else:
            keys = self.ltx.section[sect].keys.keys()

        return keys

    def complete(self, text, state):
        access_prop = text.find('.')
        if access_prop == -1:
            if state == 0:
                self._cached_lookup = list(filter(lambda x: x.startswith(text), self.top_level))
        else:
            top_level = text[:access_prop]
            prop = text[access_prop+1:]

            if state == 0:
                keys = self.get_section_keys(top_level)
                self._cached_lookup = list(map(lambda x: f'{top_level}.{x}', filter(lambda x: x.startswith(prop), keys)))

        if state >= len(self._cached_lookup) or state >= self.MAX_COMPLETION:
            return

        return self._cached_lookup[state]

def explore(ltx, st):
    comp = CompletionState(ltx, st)

    def completer(*args):
        return comp.complete(*args)

    def complete_display(*args):
        return comp.display_matches(*args)

    readline.set_completer(completer)
    readline.parse_and_bind('tab: complete')
    #readline.set_completion_display_matches_hook(complete_display)

    def print_st_key(k):
        if not isinstance(k, str) or not k.startswith("st_"):
            return k

        resolved = st.lookup(k)
        if resolved is not None:
            return "%s // %s" % (k, resolved[:70])
        else:
            return "%s // MISSING" % (k)

    xrefs = {}
    xrefs.update({k: set() for k in ltx.section.keys()})

    for t in st.table.values():
        xrefs.update({k: set() for k in t.entry.keys()})

    print("Building xrefs...")
    for sect_name, sect in ltx.section.items():
        for parent in sect.parents:
            xrefs[parent.name].add(sect_name)

        for k, v in sect.get_all().items():
            if isinstance(v, list):
                for val in v:
                    if val in xrefs:
                        xrefs[val].add(sect_name)

            elif isinstance(v, str):
                if v in xrefs:
                    xrefs[v].add(sect_name)

    while True:
        try:
            query = input("> ")
        except KeyboardInterrupt:
            print("")
            continue
        except EOFError:
            break

        query = query.strip()

        if query == "":
            continue

        if query == "exit" or query == "quit":
            break

        if query.startswith("!"):
            bang_argv = list(filter(lambda x: len(x.strip()) > 0, query[1:].split(" ")))
            bang_cmd = bang_argv[0]
            bang_argv = bang_argv[1:]

            #print(bang_cmd, bang_argv)
            if bang_cmd == "xref":
                if len(bang_argv) != 1:
                    print("error: xref requires arg")
                    continue
                xref_query = bang_argv[0]

                if xref_query not in xrefs:
                    print("error: non tracked key")
                    continue

                print(xrefs[xref_query])
            elif bang_cmd == "info":
                if len(bang_argv) != 1:
                    print("error: section required")
                    continue

                section_name = bang_argv[0]

                section = ltx.section.get(section_name)
                if section is None:
                    print("error: unknown section %s" % (query))
                    continue

                print("Parents:")
                for parent in section.parents:
                    print(" - %s" % (parent))

                classes = section.get_key_hier("class")
                if classes:
                    print("Class:")
                    for cls, sec in classes:
                        print(" - %s (%s)" % (cls, sec.name))

                kind = section.get_key_hier("kind")
                if kind:
                    print("Kind:")
                    for kind, sec in kind:
                        print(" - %s (%s)" % (kind, sec.name))

            elif bang_cmd == "search_sec":
                if len(bang_argv) != 1:
                    print("error: search_sec requires arg")
                    continue

                search_query = bang_argv[0]

                for k in filter(lambda x: fnmatch(x, search_query), ltx.section.keys()):
                    print(k)
            elif bang_cmd == "agg":
                if len(bang_argv) != 2:
                    print("error: agg section_pat field")
                    continue

                section_pat = bang_argv[0]
                field_name = bang_argv[1]

                results = {}

                for k in filter(lambda x: fnmatch(x, section_pat), ltx.section.keys()):
                    v = ltx.section[k].get(field_name)
                    if v is not None:
                        if isinstance(v, list):
                            v = ",".join(v)

                        results[v] = results.get(v, 0) + 1

                for i, (v, count) in enumerate(sorted(results.items(), key=lambda x: x[1], reverse=True)):
                    print("%d. '%s' (%d)" % (i+1, v, count))
            else:
                print("error: unknown command %s" % (bang_cmd))

            continue

        access_prop = query.find('.')

        if access_prop == -1:
            section_name = query
            prop = None
        else:
            section_name = query[:access_prop]
            prop = query[access_prop+1:]

        section = ltx.section.get(section_name)
        if section is None:
            print("error: unknown section %s" % (query))
            continue

        print(section)
        if prop:
            if '*' in prop:
                for k in filter(lambda x: fnmatch(x, prop), comp.get_section_keys(section_name)):
                    print("%s = %s" % (k, print_st_key(section.get(k))))
            elif not section.has(prop):
                print("error: missing property %s" % (prop))
            else:
                print("%s = %s" % (prop, print_st_key(section.get(prop))))

def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, help="Path to unpacked STALKER DB directory")
    parser.add_argument("--cache-dir", default=Path("./.cache/"), type=Path)
    parser.add_argument("--no-cache", action="store_true")

    args = parser.parse_args()

    gamebase = Path(args.path)
    GD = StalkerGameData(gamebase)

    if not args.no_cache:
        args.cache_dir.mkdir(exist_ok=True)
        GD.set_cache_dir(args.cache_dir)

    ltx = GD.ini_sys()
    st = GD.string_table()

    explore(ltx, st)
    return

if __name__ == "__main__":
    main()
