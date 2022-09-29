from setuptools import setup, find_packages
from glob import glob

setup(
    name="Diffenator2",
    version="0.0.1",
    url="https://github.com/m4rc1e/diffenator2",
    author="Marc Foley",
    author_email="m.foley.88@gmail.com",
    description="Compare two fonts.",
    packages=find_packages(),
    install_requires=[
        "FontTools[ufo]",
        "fontFeatures[shaper]",
        "jinja2",
        "blackrenderer[skia]",
        "Pillow",
        "uharfbuzz",
        "pyahocorasick",
        "selenium>=4.4.3",
        "ninja",
        "protobuf==3.19.2",
        "gflanguages"
    ],
    package_dir={"diffenator": "diffenator"},
    package_data={
        "diffenator": ["data/wordlists/*.txt", "templates/*", "data/*.txt"],
    },
    scripts=glob("bin/*"),
)
