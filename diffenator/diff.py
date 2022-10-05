from diffenator.shape import test_words
from diffenator.shape import test_fonts
from diffenator.font import DFont
from diffenator import jfont


class DiffFonts:
    def __init__(self, old_font: DFont, new_font: DFont):
        self.old_font = old_font
        self.new_font = new_font

    def diff_all(self):
        skip = frozenset(["diff_strings", "diff_all"])
        diff_funcs = [f for f in dir(self) if f.startswith("diff_") if f not in skip]
        for f in diff_funcs:
            eval(f"self.{f}()")

    def diff_tables(self):
        self.tables = jfont.Diff(self.old_font.jFont, self.new_font.jFont)

    def diff_strings(self, fp):
        self.strings = test_words(fp, self.old_font, self.new_font, threshold=0.0)

    def diff_words(self):
        self.glyph_diff = test_fonts(self.old_font, self.new_font)

    def to_html(self, templates, out):
        from diffenator.html import diffenator_report

        diffenator_report(self, templates, dst=out)