from __future__ import annotations
import logging
import os
from ninja.ninja_syntax import Writer
from diffenator2.renderer import FONT_SIZE
from diffenator2.utils import dict_coords_to_string
from diffenator2.font import DFont, get_font_styles
from diffenator2.utils import partition
from diffenator2.matcher import FontMatcher
from pkg_resources import resource_filename
import shutil
import ninja


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


MAX_STYLES = 1
THRESHOLD = 0.90  # Percent difference
NINJA_BUILD_FILE = "build.ninja"


class NinjaBuilder:
    NINJA_LOG_FILE = ".ninja_log"
    NINJA_BUILD_FILE = "build.ninja"

    def __init__(self, cli_args):
        self.cli_args = cli_args
        self.ninja_file = open(NINJA_BUILD_FILE, "w", encoding="utf8")
        self.w = Writer(self.ninja_file)

    def run(self):
        self.w.close()
        ninja._program("ninja", [])

    def proof_fonts(self):
        self.ninja_file = open(NINJA_BUILD_FILE, "w", encoding="utf8")
        self.w = Writer(self.ninja_file)
        self.w.rule("proofing", '_diffbrowsers "$args"')
        self.w.newline()
        self.w.build(self.cli_args["out"], "proofing", variables={"args": repr(self.cli_args)})
        self.run()
        self.w.close()
        self.ninja_file.close()

    def diff_fonts(self, fonts_before, fonts_after):
        self.ninja_file = open(NINJA_BUILD_FILE, "w", encoding="utf8")
        self.w = Writer(self.ninja_file)
        if self.cli_args["diffbrowsers"]:
            self.w.rule("diffbrowsers", '_diffbrowsers "$args"')
            self.w.build(self.cli_args["out"], "diffbrowsers", variables={"args": repr(self.cli_args)})
        self.w.newline()

        if self.cli_args["diffenator"]:
            self.w.rule("diffenator", '_diffenator "$args"')
            matcher = FontMatcher(fonts_before, fonts_after)

            getattr(matcher, self.cli_args["styles"])(self.cli_args["filter_styles"])
            for old_style, new_style in zip(matcher.old_styles, matcher.new_styles):
                coords = new_style.coords
                style = new_style.name.replace(" ", "-")
                o = os.path.join(self.cli_args["out"], style.replace(" ", "-"))
                self.w.build(o, "diffenator", variables={"args": repr(
                    {**self.cli_args, **{
                        "coords": dict_coords_to_string(coords),
                        "old_font": old_style.font.ttFont.reader.file.name,
                        "new_font": new_style.font.ttFont.reader.file.name,
                        "out": self.cli_args["out"],
                    }}
                )})
        self.run()
        self.w.close()
        self.ninja_file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # rm ninja cache files so we can rerun the tool
        self.ninja_file.close()
        if os.path.exists(self.NINJA_BUILD_FILE):
            os.remove(self.NINJA_BUILD_FILE)
        if os.path.exists(self.NINJA_LOG_FILE):
            os.remove(self.NINJA_LOG_FILE)


def ninja_proof(
    fonts,
    out: str = "out",
    styles="instances",
    filter_styles: str = "",
    characters: str = ".*",
    pt_size: int = 20,
    command="proof",
    user_wordlist: str = "",
    diffbrowsers_templates=[],
    **kwargs
):
    if not os.path.exists(out):
        os.mkdir(out)

    args = {
        **locals(),
        **locals().pop("kwargs"),
        **{"fonts": [f.path for f in fonts]}
    }
    with NinjaBuilder(cli_args=args) as builder:
        if filter_styles:
            builder.proof_fonts()
            return

        font_styles = get_font_styles(fonts, styles)
        partitioned = partition(font_styles, MAX_STYLES)
        for font_styles in partitioned:
            filter_styles = "|".join(s.name for s in font_styles)
            builder.cli_args["out"] = out
            builder.cli_args["filter_styles"] = filter_styles
            builder.proof_fonts()


def ninja_diff(
    fonts_before: list[DFont],
    fonts_after: list[DFont],
    diffbrowsers: bool = True,
    diffenator: bool = True,
    out: str = "out",
    imgs: bool = False,
    styles: str = "instances",
    characters: str = ".*",
    user_wordlist: str = "",
    filter_styles: str = "",
    font_size: int = 20,
    pt_size: int = 20,
    threshold: float = THRESHOLD,
    precision: int = FONT_SIZE,
    no_words: bool = False,
    no_tables: bool = False,
    diffenator_template = resource_filename(
        "diffenator2", os.path.join("templates", "diffenator.html")
    ),
    command="diff",
    diffbrowsers_templates=[],
    debug_gifs: bool = False,
    **kwargs
):
    args = {
        **locals(),
        **locals().pop("kwargs"),
        **{"fonts_before": [f.path for f in fonts_before]},
        **{"fonts_after": [f.path for f in fonts_after]}
    }
    if not os.path.exists(out):
        os.mkdir(out)

    with NinjaBuilder(cli_args=args) as builder:
        if filter_styles:
            builder.diff_fonts(fonts_before, fonts_after)
            return

    matcher = FontMatcher(fonts_before, fonts_after)
    getattr(matcher, styles)()
    if not matcher.old_styles and not matcher.new_styles:
        raise ValueError(
            f"Matcher was not able to detect any matching styles for {styles} "
            "method.\nPlease ensure that variable fonts have fvar instances, "
            "both fonts have designspaces which overlap or ensure that both "
            "sets of static fonts have some matching styles."
        )

    partitioned = partition(matcher.old_styles, MAX_STYLES)
    for p in partitioned:
        filter_styles = "|".join(style.name for style in p)
        builder.cli_args["out"] = out
        builder.cli_args["filter_styles"] = filter_styles
        builder.diff_fonts(fonts_before, fonts_after)
