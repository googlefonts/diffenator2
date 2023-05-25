#!/usr/bin/env python3
"""
diffenator2
"""
from __future__ import annotations
from diffenator2.utils import string_coords_to_dict, re_filter_characters, characters_in_string
from diffenator2.font import DFont
from diffenator2.matcher import FontMatcher
from pkg_resources import resource_filename
import os
from diffenator2.shape import test_words, test_fonts
from diffenator2 import jfont, THRESHOLD
from diffenator2.html import diffenator_report
import fire


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

    def filter_characters(self, characters):
        diff_words = self.glyph_diff["words"]
        for cat in diff_words:
            diff_words[cat] = [i for i in diff_words[cat] if characters_in_string(i.string, characters)]
        
        diff_glyphs = self.glyph_diff["glyphs"]
        diff_glyphs.new = [g for g in diff_glyphs.new if characters_in_string(g.string, characters)]
        diff_glyphs.missing = [g for g in diff_glyphs.missing if characters_in_string(g.string, characters)]
        diff_glyphs.modified = [g for g in diff_glyphs.modified if characters_in_string(g.string, characters)]

    def to_html(self, templates, out):
        diffenator_report(self, templates, dst=out)


def main(**kwargs):
    if "coords" in kwargs:
        coords = string_coords_to_dict(kwargs["coords"])
    else:
        coords = None

    old_font = DFont(os.path.abspath(kwargs["old_font"]), suffix="old")
    new_font = DFont(os.path.abspath(kwargs["new_font"]), suffix="new")
    matcher = FontMatcher([old_font], [new_font])
    matcher.diffenator(coords)
    matcher.upms()

    diff = DiffFonts(matcher, threshold=kwargs.get("threshold", 0.01))
    diff.diff_all()
    if "user_wordlist" in kwargs:
        diff.diff_strings(kwargs["user_wordlist"])
    
    characters = re_filter_characters(new_font, kwargs.get("characters", ".*"))
    diff.filter_characters(characters)
    diff.to_html(
        kwargs.get("template", resource_filename("diffenator2",
            os.path.join("templates", "diffenator.html")
            ),
        ),
        kwargs.get("out", "out")
    )


if __name__ == "__main__":
    fire.Fire(main)
