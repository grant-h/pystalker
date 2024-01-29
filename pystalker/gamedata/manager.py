import hashlib
import pickle
import pystalker.gamedata.ltx
import pystalker.gamedata.string_table

from pathlib import Path

class StalkerGameData:
    def __init__(self, gamebase):
        self.gamebase = Path(gamebase)
        self._string_table = {}
        self._ini_sys = None
        self._ini_cache_dir = None

    def set_cache_dir(self, cache_dir):
        self._ini_cache_dir = Path(cache_dir)

    def open_texture(self, path):
        from PIL import Image
        path = Path(path)

        if path.suffix:
            return Image.open(self.gamebase / "textures" / path)
        else:
            return Image.open((self.gamebase / "textures" / path).with_suffix(".dds"))

    def ini_sys(self):
        if self._ini_sys:
            return self._ini_sys

        ltx = self.load_ini("system.ltx")
        self._ini_sys = ltx
        return ltx

    def load_ini(self, path):
        path = self.gamebase / "configs" / path

        if self._ini_cache_dir:
            return self._load_ini_cached(path)
        else:
            return self._load_ini(path)

    def _load_ini(self, path):
        ltx = pystalker.gamedata.ltx.LTXFileRoot(path)
        ltx.parse()
        return ltx

    def _load_ini_cached(self, path):
        path = Path(path)

        base_name = path.name.replace(".", "_")
        cache_name = self._ini_cache_dir / Path(base_name + "_" + hashlib.md5(open(path, 'rb').read()).hexdigest())

        if cache_name.exists():
            ltx = pickle.load(open(cache_name, 'rb'))
            return ltx
        else:
            ltx = self._load_ini(path)
            pickle.dump(ltx, open(cache_name, 'wb'))

        return ltx

    def string_table(self, lang="eng"):
        if lang in self._string_table:
            return self._string_table[lang]

        stg = pystalker.gamedata.string_table.StringTableGroup(self.gamebase / "configs/text" / lang)
        stg.walk()

        self._string_table[lang] = stg
        return stg

    def st_lookup(self, key, lang="eng"):
        return self.string_table(lang=lang).lookup(key)

