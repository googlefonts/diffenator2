#!/usr/bin/env python3
"""
diffenator2
"""
from __future__ import annotations
from diffenator2.utils import string_coords_to_dict
from diffenator2.font import DFont, Style
from diffenator2.matcher import FontMatcher
from pkg_resources import resource_filename
import os
import argparse
from diffenator2.shape import test_words, test_fonts
from diffenator2.font import DFont
from diffenator2 import jfont, THRESHOLD
from diffenator2.html import diffenator_report


class DiffFonts:
    def __init__(self, matcher, threshold=0.01):
        self.old_font = matcher.old_fonts[0]
        self.new_font = matcher.new_fonts[0]

        self.old_style = matcher.old_styles[0]
        self.new_style = matcher.new_styles[0]
        self.threshold = threshold

    def diff_all(self):
        skip = frozenset(["diff_strings", "diff_all"])
        diff_funcs = [f for f in dir(self) if f.startswith("diff_") if f not in skip]
        for f in diff_funcs:
            getattr(self,f)()

    def diff_tables(self):
        self.tables = jfont.Diff(self.old_font.jFont, self.new_font.jFont)

    def diff_strings(self, fp):
        self.strings = test_words(fp, self.old_font, self.new_font, threshold=self.threshold)

    def diff_words(self):
        self.glyph_diff = test_fonts(self.old_font, self.new_font, threshold=self.threshold)

    def to_html(self, templates, out, assets_dir):
        diffenator_report(self, templates, dst=out, assets_dir=assets_dir)


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
    parser.add_argument("--threshold", "-t", default=THRESHOLD, type=float)
    parser.add_argument("--out", "-o", default="out", help="Output html path")
    parser.add_argument("--assets-dir", help="Where to put font assets")
    args = parser.parse_args()

    if not args.assets_dir:
        args.assets_dir = args.out

    coords = string_coords_to_dict(args.coords) if args.coords else None

    old_font = DFont(os.path.abspath(args.old_font), suffix="old")
    new_font = DFont(os.path.abspath(args.new_font), suffix="new")
    matcher = FontMatcher([old_font], [new_font])
    matcher.diffenator(coords)
    matcher.upms()

    diff = DiffFonts(matcher, threshold=args.threshold)
    diff.diff_all()
    if args.user_wordlist:
        diff.diff_strings(args.user_wordlist)
    diff.to_html(args.template, args.out, assets_dir=args.assets_dir)


if __name__ == "__main__":
    main()
