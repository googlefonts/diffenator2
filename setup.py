from setuptools import setup, find_packages
from glob import glob
import os

setup(
    name="Diffenator2",
    version="0.0.1",
    url="https://github.com/m4rc1e/diffenator2",
    author="Marc Foley",
    author_email="m.foley.88@gmail.com",
    description="Compare two fonts.",
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
        "protobuf>=3.19.2",
        "gflanguages",
        "freetype-py",
    ],
    packages=find_packages(),
    package_dir={"diffenator": "diffenator"},
    package_data={
        "diffenator": [
            os.path.join("data", "wordlists", "*.txt"),
            os.path.join("templates", "*"),
            os.path.join("data", "*.txt")
        ],
    },
    entry_points = {
        'console_scripts': [
            'diffbrowsers=diffenator.diffbrowsers:main',
            'diffenator=diffenator.diffenatorscript:main',
            'diffenator2=diffenator.diffenator2:main',
        ],
    }
)
