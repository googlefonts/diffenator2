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

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.w = Writer(open(NINJA_BUILD_FILE, "w", encoding="utf8"))

    def add_rule(self, name, string):
        cmd = self.populate_cli_command(string)
        self.w.comment("Rules")
        self.w.newline()
        self.w.rule(name, cmd)
        self.w.newline()

    def build(self, out, name, varss):
        # Setup build
        self.w.comment("Build rules")
        variables = {
            **{k: v for k, v in self.__dict__.items() if k not in ["command", "w"]},
            **varss,
        }
        self.w.build(out, name, variables=variables)

    def run(self):
        self.w.close()
        ninja._program("ninja", [])

    def proof_fonts(self, fonts):
        self.w = Writer(open(NINJA_BUILD_FILE, "w", encoding="utf8"))
        self.add_rule("proofing", "_diffbrowsers proof $fonts")
        varss = {
            "fonts": [f'"{os.path.abspath(f.ttFont.reader.file.name)}"' for f in fonts]
        }
        self.build("proofing", varss)
        self.run()

    def diff_fonts(self, fonts_before, fonts_after):
        self.w = Writer(open(NINJA_BUILD_FILE, "w", encoding="utf8"))
        self.add_rule(
            "diffbrowsers", "_diffbrowsers diff -fb $fonts_before -fa $fonts_after"
        )
        varss = {
            "fonts_before": [
                f'"{os.path.abspath(f.ttFont.reader.file.name)}"' for f in fonts_before
            ],
            "fonts_after": [
                f'"{os.path.abspath(f.ttFont.reader.file.name)}"' for f in fonts_after
            ],
        }
        self.build(self.out, "diffbrowsers", varss)
        
        self.add_rule(
            "diffenator", "_diffenator $font_before $font_after"
        )
        
        matcher = FontMatcher(fonts_before, fonts_after)
        getattr(matcher, self.styles)(self.filter_styles)
        for old_style, new_style in zip(matcher.old_styles, matcher.new_styles):
            coords = new_style.coords
            style = new_style.name.replace(" ", "-")
            diff_vars = {
                "font_before": f'"{old_style.font.ttFont.reader.file.name}"',
                "font_after": f'"{new_style.font.ttFont.reader.file.name}"',
            }
            # Fix this shit
            self.fonts_before = None
            self.fonts_after = None
            o = os.path.join(self.out, style.replace(" ", "-"))
            self.build(o, "diffenator", diff_vars)
        self.run()

    def populate_cli_command(self, cmd):
        for k, v in vars(self).items():
            k = k.replace("_", "-")
            if any([not v, k == "w", k == "command"]):
                continue
            elif isinstance(v, bool):
                cmd += f" --{k}"
            elif isinstance(v, (str, int, float)):
                cmd += f' --{k} "${k}"'
        return cmd

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

    with NinjaBuilder(**kwargs) as builder:
        if kwargs["filter_styles"]:
            builder.proof_fonts(kwargs["fonts"])
            return

        font_styles = get_font_styles(kwargs["fonts"], kwargs["styles"])
        partitioned = partition(font_styles, MAX_STYLES)
        for font_styles in partitioned:
            filter_styles = "|".join(s.name for s in font_styles)
            o = os.path.join(kwargs["out"], filter_styles.replace("|", "-"))
            if not os.path.exists(o):
                os.mkdir(o)
            builder.out = o
            builder.filter_styles = filter_styles
            builder.proof_fonts(kwargs["fonts"])


def ninja_diff(**kwargs):
    if not os.path.exists(kwargs["out"]):
        os.mkdir(kwargs["out"])

    with NinjaBuilder(**kwargs) as builder:
        if kwargs["filter_styles"]:
            builder.diff_fonts(kwargs["fonts_before"], kwargs["fonts_after"])
            return

    matcher = FontMatcher(kwargs["fonts_before"], kwargs["fonts_after"])
    getattr(matcher, kwargs["styles"])()
    if not matcher.old_styles and not matcher.new_styles:
        raise ValueError(
            f"Matcher was not able to detect any matching styles for {kwargs['styles']} "
            "method.\nPlease ensure that variable fonts have fvar instances, "
            "both fonts have designspaces which overlap or ensure that both "
            "sets of static fonts have some matching styles."
        )

    partitioned = partition(matcher.old_styles, MAX_STYLES)
    for p in partitioned:
        filter_styles = "|".join(style.name for style in p)
        o = os.path.join(kwargs["out"], filter_styles.replace("|", "-"))
        if not os.path.exists(o):
            os.mkdir(o)
        builder.out = o
        builder.filter_styles = filter_styles
        builder.diff_fonts(kwargs["fonts_before"], kwargs["fonts_after"])

