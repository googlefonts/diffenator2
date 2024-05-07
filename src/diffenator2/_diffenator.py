#!/usr/bin/env python3
"""
diffenator2
"""
from __future__ import annotations
from diffenator2.renderer import FONT_SIZE
from diffenator2.utils import (
    string_coords_to_dict,
    re_filter_characters,
    characters_in_string,
)
from diffenator2.font import DFont
from diffenator2.matcher import FontMatcher
from pkg_resources import resource_filename
import os
from diffenator2.shape import test_words, test_fonts
from diffenator2 import jfont, THRESHOLD
from diffenator2.html import diffenator_report
import types
import ast
import sys


class DiffFonts:
    def __init__(self, matcher, threshold=0.01, font_size=28, words=True, tables=True, debug_gifs=False):
        self.old_font = matcher.old_fonts[0]
        self.new_font = matcher.new_fonts[0]

        self.old_style = matcher.old_styles[0]
        self.new_style = matcher.new_styles[0]
        self.threshold = threshold
        self.do_words = words
        self.do_tables = tables
        self.font_size = font_size
        self.debug_gifs = debug_gifs

    def diff_all(self):
        self.diff_tables()
        self.diff_words()

    def diff_tables(self):
        if not self.do_tables:
            self.tables = jfont.Diff({}, {})
            return
        self.tables = jfont.Diff(self.old_font.jFont, self.new_font.jFont)

    def diff_strings(self, fp):
        self.strings = test_words(
            fp,
            self.old_font,
            self.new_font,
            threshold=self.threshold,
            font_size=self.font_size,
        )

    def diff_words(self):
        self.glyph_diff = test_fonts(
            self.old_font,
            self.new_font,
            threshold=self.threshold,
            do_words=self.do_words,
            font_size=self.font_size,
            debug_gifs=self.debug_gifs,
        )

    def filter_characters(self, characters):
        diff_words = self.glyph_diff["words"]
        for cat in diff_words:
            diff_words[cat] = [
                i for i in diff_words[cat] if characters_in_string(i.string, characters)
            ]

        diff_glyphs = self.glyph_diff["glyphs"]
        diff_glyphs.new = [
            g for g in diff_glyphs.new if characters_in_string(g.string, characters)
        ]
        diff_glyphs.missing = [
            g for g in diff_glyphs.missing if characters_in_string(g.string, characters)
        ]
        diff_glyphs.modified = [
            g
            for g in diff_glyphs.modified
            if characters_in_string(g.string, characters)
        ]

    def to_html(self, templates, out):
        diffenator_report(self, templates, dst=out)


def main():
    # Maybe json load/dump is better
    args = types.SimpleNamespace(**ast.literal_eval(sys.argv[1]))

    coords = string_coords_to_dict(args.coords)

    old_font = DFont(os.path.abspath(args.old_font), suffix="old")
    new_font = DFont(os.path.abspath(args.new_font), suffix="new")
    matcher = FontMatcher([old_font], [new_font])
    matcher.diffenator(coords)
    matcher.upms()

    diff = DiffFonts(
        matcher,
        words=not args.no_words,
        tables=not args.no_tables,
        threshold=args.threshold,
        font_size=args.font_size,
        debug_gifs=args.debug_gifs,
    )
    diff.diff_all()
    if args.user_wordlist:
        diff.diff_strings(args.user_wordlist)

    characters = re_filter_characters(new_font, args.characters)
    diff.filter_characters(characters)
    diff.to_html(args.diffenator_template, args.out)


if __name__ == "__main__":
    main()
