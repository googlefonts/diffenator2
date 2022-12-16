#!/usr/bin/env python3
"""
diffenator2
"""
from __future__ import annotations
from diffenator2.utils import string_coords_to_dict
from diffenator2.font import DFont, match_fonts
from pkg_resources import resource_filename
import os
import argparse
from diffenator2.shape import test_words, test_fonts
from diffenator2.font import DFont
from diffenator2 import jfont
from diffenator2.html import diffenator_report


class DiffFonts:
    def __init__(self, old_font: DFont, new_font: DFont):
        self.old_font = old_font
        self.new_font = new_font

    def diff_all(self):
        skip = frozenset(["diff_strings", "diff_all"])
        diff_funcs = [f for f in dir(self) if f.startswith("diff_") if f not in skip]
        for f in diff_funcs:
            getattr(self,f)()

    def diff_tables(self):
        self.tables = jfont.Diff(self.old_font.jFont, self.new_font.jFont)

    def diff_strings(self, fp):
        self.strings = test_words(fp, self.old_font, self.new_font, threshold=0.5)

    def diff_words(self):
        self.glyph_diff = test_fonts(self.old_font, self.new_font)

    def to_html(self, templates, out):
        diffenator_report(self, templates, dst=out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("old_font")
    parser.add_argument("new_font")
    parser.add_argument(
        "--template",
        default=resource_filename(
            "diffenator2", os.path.join("templates", "diffenator.html")
        ),
    )
    parser.add_argument(
        "--user-wordlist", help="File of strings to visually compare", default=None
    )
    parser.add_argument("--coords", "-c", default={})
    parser.add_argument("--out", "-o", default="out", help="Output html path")
    args = parser.parse_args()

    coords = string_coords_to_dict(args.coords)

    old_font = DFont(os.path.abspath(args.old_font))
    new_font = DFont(os.path.abspath(args.new_font))
    match_fonts(old_font, new_font, variations=coords, scale_upm=True)

    diff = DiffFonts(old_font, new_font)
    diff.diff_all()
    if args.user_wordlist:
        diff.diff_strings(args.user_wordlist)
    diff.to_html(args.template, args.out)


if __name__ == "__main__":
    main()
