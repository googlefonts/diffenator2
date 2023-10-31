from __future__ import annotations
import logging
import os
from ninja.ninja_syntax import Writer
from diffenator2.renderer import FONT_SIZE
from diffenator2.utils import dict_coords_to_string
from diffenator2.font import DFont, get_font_styles
from diffenator2.utils import partition
from diffenator2.matcher import FontMatcher
import shutil
import ninja

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


MAX_STYLES = 4
THRESHOLD = 0.90  # Percent difference
NINJA_BUILD_FILE = "build.ninja"


class NinjaBuilder:
    NINJA_LOG_FILE = ".ninja_log"
    NINJA_BUILD_FILE = "build.ninja"

    def __init__(self, cli_args):
        self.cli_args = cli_args
        self.w = Writer(open(NINJA_BUILD_FILE, "w", encoding="utf8"))

    def run(self):
        self.w.close()
        ninja._program("ninja", [])

    def proof_fonts(self):
        self.w = Writer(open(NINJA_BUILD_FILE, "w", encoding="utf8"))
        self.w.rule("proofing", '_diffbrowsers "$args"')
        self.w.newline()
        self.w.build(self.cli_args["out"], "proofing", variables={"args": repr(self.cli_args)})
        self.run()

    def diff_fonts(self, fonts_before, fonts_after):
        self.w = Writer(open(NINJA_BUILD_FILE, "w", encoding="utf8"))
        self.w.rule("diffbrowsers", '_diffbrowsers "$args"')
        self.w.build(self.cli_args["out"], "diffbrowsers", variables={"args": repr(self.cli_args)})
        self.run()
#        
#        self.add_rule(
#            "diffenator", "_diffenator"
#        )
#        
#        matcher = FontMatcher(fonts_before, fonts_after)
#        getattr(matcher, self.styles)(self.filter_styles)
#        for old_style, new_style in zip(matcher.old_styles, matcher.new_styles):
#            coords = new_style.coords
#            style = new_style.name.replace(" ", "-")
#            diff_vars = {
#                "font_before": f'"{old_style.font.ttFont.reader.file.name}"',
#                "font_after": f'"{new_style.font.ttFont.reader.file.name}"',
#            }
#            # Fix this shit
#            self.fonts_before = None
#            self.fonts_after = None
#            o = os.path.join(self.out, style.replace(" ", "-"))
#            self.build_rules(o, "diffenator", diff_vars)
#        self.run()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # rm ninja cache files so we can rerun the tool
        if os.path.exists(self.NINJA_BUILD_FILE):
            os.remove(self.NINJA_BUILD_FILE)
        if os.path.exists(self.NINJA_LOG_FILE):
            os.remove(self.NINJA_LOG_FILE)


def ninja_proof(**kwargs):
    if not os.path.exists(kwargs["out"]):
        os.mkdir(kwargs["out"])

    with NinjaBuilder(cli_args=kwargs) as builder:
        if kwargs["filter_styles"]:
            builder.proof_fonts()
            return

        dfonts = [DFont(f) for f in kwargs["fonts"]]
        font_styles = get_font_styles(dfonts, kwargs["styles"])
        partitioned = partition(font_styles, MAX_STYLES)
        out = kwargs["out"]
        for font_styles in partitioned:
            filter_styles = "|".join(s.name for s in font_styles)
            o = os.path.join(out, filter_styles.replace("|", "-"))
            if not os.path.exists(o):
                os.mkdir(o)
            builder.cli_args["out"] = o
            builder.cli_args["filter_styles"] = filter_styles
            builder.proof_fonts()

def ninja_diff(**kwargs):
    if not os.path.exists(kwargs["out"]):
        os.mkdir(kwargs["out"])

    with NinjaBuilder(cli_args=kwargs) as builder:
        if kwargs["filter_styles"]:
            builder.diff_fonts(kwargs["fonts_before"], kwargs["fonts_after"])
            return

    fonts_before = [DFont(f) for f in kwargs["fonts_before"]]
    fonts_after = [DFont(f) for f in kwargs["fonts_after"]]
    matcher = FontMatcher(fonts_before, fonts_after)
    getattr(matcher, kwargs["styles"])()
    if not matcher.old_styles and not matcher.new_styles:
        raise ValueError(
            f"Matcher was not able to detect any matching styles for {kwargs['styles']} "
            "method.\nPlease ensure that variable fonts have fvar instances, "
            "both fonts have designspaces which overlap or ensure that both "
            "sets of static fonts have some matching styles."
        )

    partitioned = partition(matcher.old_styles, MAX_STYLES)
    out = kwargs["out"]
    for p in partitioned:
        filter_styles = "|".join(style.name for style in p)
        o = os.path.join(out, filter_styles.replace("|", "-"))
        if not os.path.exists(o):
            os.mkdir(o)
        builder.cli_args["out"] = o
        builder.cli_args["filter_styles"] = filter_styles
        builder.diff_fonts(kwargs["fonts_before"], kwargs["fonts_after"])
