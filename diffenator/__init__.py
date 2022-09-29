"""
Diffenator is primarily a visual differ. Its main job is to stop users reporting visual issues to google/fonts.

What should be checked:

- Essential tables e.g OS/2, hhea attribs (Simon seemed keen on this so discuss implementation of this in the context of what I've found here)

Output:
- A single html page. No images, just pure html and js.
"""
from diffenator.shape import test_words
from diffenator.shape import test_fonts
from diffenator.font import DFont
from diffenator import jfont
import logging
import os
import tempfile
import ninja
from ninja.ninja_syntax import Writer
from diffenator.screenshot import screenshot_dir


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def dict_coords_to_string(coords):
    return ",".join(f"{k}={v}" for k, v in coords.items())


def run_proofing_tools(fonts, out="out", imgs=True):
    if not os.path.exists(out):
        os.mkdir(out)

    with tempfile.TemporaryDirectory() as dir_:
        w = Writer(open(os.path.join(dir_, "build.ninja"), "w"))
        w.comment("Rules")
        w.newline()
        w.rule("proofing", "diffbrowsers proof $fonts -o $out/diffbrowsers")
        w.newline()

        # Setup build
        w.comment("Build rules")
        w.build(
            out,
            "proofing",
            variables=dict(
                fonts=[f.reader.file.name for f in fonts],
                out=out,
            ),
        )
        w.close()
        os.chdir(dir_)
        ninja._program("ninja", [])
        if imgs:
            screenshot_dir(out, os.path.join(out, "imgs"))


def run_diffing_tools(
    fonts_before, fonts_after=None, diffbrowsers=True, diffenator=True, out="out", imgs=True,
):
    if not os.path.exists(out):
        os.mkdir(out)

    with tempfile.TemporaryDirectory() as dir_:
        w = Writer(open(os.path.join(dir_, "build.ninja"), "w"))
        # Setup rules
        w.comment("Rules")
        w.newline()
        w.comment("Build Hinting docs")
        w.rule(
            "diffbrowsers",
            "diffbrowsers diff -fb $fonts_before -fa $fonts_after -o $out/diffbrowsers",
        )
        w.newline()

        w.comment("Build Proofing docs")
        w.rule("proofing", "diffbrowsers proof $fonts -o $out/diffbrowsers")
        w.newline()

        w.comment("Run diffenator")
        w.rule("diffenator", "diffenator $font_before $font_after -c $coords -o $out")
        w.newline()

        # Setup build
        w.comment("Build rules")
        if diffbrowsers:
            w.build(
                out,
                "diffbrowsers",
                variables=dict(
                    fonts_before=[os.path.abspath(f.reader.file.name) for f in fonts_before],
                    fonts_after=[os.path.abspath(f.reader.file.name) for f in fonts_after],
                    out=out,
                ),
            )
        if diffenator:
            for style, font_before, font_after, coords in matcher(
                fonts_before, fonts_after
            ):
                style = style.replace(" ", "-")
                w.build(
                    os.path.join(out, style),
                    "diffenator",
                    variables=dict(
                        font_before=font_before,
                        font_after=font_after,
                        coords=dict_coords_to_string(coords),
                        out=style,
                    ),
                )
        w.close()
        os.chdir(dir_)
        ninja._program("ninja", [])
        if imgs:
            screenshot_dir(out, os.path.join(out, "imgs"))


def _fullname(ttfont):
    return (
        f"{ttfont['name'].getBestFamilyName()} {ttfont['name'].getBestSubFamilyName()}"
    )


def _vf_fullnames(ttfont):
    assert "fvar" in ttfont
    res = []
    family_name = ttfont["name"].getBestFamilyName()
    instances = ttfont["fvar"].instances
    for inst in instances:
        name_id = inst.subfamilyNameID
        name = ttfont["name"].getName(name_id, 3, 1, 0x409).toUnicode()
        res.append((f"{family_name} {name}", inst.coordinates))
    return res


def matcher(fonts_before, fonts_after):
    before = {}
    after = {}
    for font in fonts_before:
        if "fvar" in font:
            vf_names = _vf_fullnames(font)
            for n, coords in vf_names:
                before[n] = (os.path.abspath(font.reader.file.name), coords)
        else:
            before[_fullname(font)] = (os.path.abspath(font.reader.file.name), {})

    for font in fonts_after:
        if "fvar" in font:
            vf_names = _vf_fullnames(font)
            for n, coords in vf_names:
                after[n] = (os.path.abspath(font.reader.file.name), coords)
        else:
            after[_fullname(font)] = (os.path.abspath(font.reader.file.name), {})

    shared = set(before.keys()) & set(after.keys())
    res = []
    for style in shared:
        res.append((style, before[style][0], after[style][0], after[style][1]))
    return res


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
