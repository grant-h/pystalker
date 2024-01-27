import io
import os
from setuptools import find_packages, setup

def read(*paths, **kwargs):
    content = ""
    with io.open(
        os.path.join(os.path.dirname(__file__), *paths),
        encoding=kwargs.get("encoding", "utf8"),
    ) as open_file:
        content = open_file.read().strip()
    return content

def get_version():
    g = {}
    exec(read("pystalker", "_version.py"), g)
    return g["__VERSION__"]

setup(
    name="pystalker",
    version=get_version(),
    description="A Python library to parse various files from the S.T.A.L.K.E.R series of games, including mods like Anomaly and GAMMA.",
    url="https://github.com/grant-h/pystalker/",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Grant Hernandez",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        "console_scripts": ["pystalker = pystalker.cli:main"]
    },
)
