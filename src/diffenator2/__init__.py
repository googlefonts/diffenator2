from __future__ import annotations
import logging
import os
from ninja.ninja_syntax import Writer
from diffenator2.utils import dict_coords_to_string
from diffenator2.font import DFont, get_font_styles
from diffenator2.utils import partition
from diffenator2.matcher import FontMatcher
import ninja

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


MAX_STYLES = 4
THRESHOLD = 0.90  # Percent difference
NINJA_BUILD_FILE = "build.ninja"


def ninja_proof(
    fonts: list[DFont],
    out: str = "out",
    imgs: bool = False,
    styles="instances",
    filter_styles: str = "",
    characters: str = ".*",
    pt_size: int = 20,
):
    if not os.path.exists(out):
        os.mkdir(out)

    if filter_styles:
        _ninja_proof(fonts, out, imgs, styles, filter_styles, characters, pt_size)
        return

    font_styles = get_font_styles(fonts, styles)
    partitioned = partition(font_styles, MAX_STYLES)
    for font_styles in partitioned:
        filter_styles = "|".join(s.name for s in font_styles)
        o = os.path.join(out, filter_styles.replace("|", "-"))
        if not os.path.exists(o):
            os.mkdir(o)
        _ninja_proof(fonts, o, imgs, styles, filter_styles, characters, pt_size)


def _ninja_proof(
    fonts: list[DFont],
    out: str = "out",
    imgs: bool = False,
    styles: str = "instances",
    filter_styles: str = "",
    characters=".*",
    pt_size: int = 20,
):
    w = Writer(open(NINJA_BUILD_FILE, "w", encoding="utf8"))
    w.comment("Rules")
    w.newline()
    out_s = os.path.join("out", "diffbrowsers")

    cmd = f'_diffbrowsers proof $fonts -s $styles -o $out -pt $pt_size -ch "$characters"'
    if imgs:
        cmd += " --imgs"
    if filter_styles:
        cmd += f' --filter-styles "$filters"'
    w.rule("proofing", cmd)
    w.newline()

    # Setup build
    w.comment("Build rules")
    variables = dict(
        fonts=[f'"{os.path.abspath(f.ttFont.reader.file.name)}"' for f in fonts],
        styles=styles,
        out=out_s,
        pt_size=pt_size,
        characters=characters,
    )
    if imgs:
        variables["imgs"] = imgs
    if filter_styles:
        variables["filters"] = filter_styles
    w.build(out, "proofing", variables=variables)
    w.close()
    ninja._program("ninja", [])


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
    pt_size: int = 20,
    threshold: float = THRESHOLD,
):
    if not os.path.exists(out):
        os.mkdir(out)

    if filter_styles:
        _ninja_diff(
            fonts_before,
            fonts_after,
            diffbrowsers,
            diffenator,
            out,
            imgs,
            styles,
            characters,
            user_wordlist,
            filter_styles,
            pt_size,
            threshold=threshold,
        )
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
        o = os.path.join(out, filter_styles.replace("|", "-"))
        if not os.path.exists(o):
            os.mkdir(o)
        _ninja_diff(
            fonts_before,
            fonts_after,
            diffbrowsers,
            diffenator,
            o,
            imgs,
            styles,
            characters,
            user_wordlist,
            filter_styles,
            pt_size,
            threshold=threshold,
        )

def _ninja_diff(
    fonts_before: list[DFont],
    fonts_after: list[DFont],
    diffbrowsers: bool = True,
    diffenator: bool = True,
    out: str = "out",
    imgs: bool = False,
    styles="instances",
    characters=".*",
    user_wordlist: str = "",
    filter_styles: str = "",
    pt_size: int = 20,
    threshold: float = THRESHOLD,
):
    w = Writer(open(NINJA_BUILD_FILE, "w", encoding="utf8"))
    # Setup rules
    w.comment("Rules")
    w.newline()
    w.comment("Build Hinting docs")
    db_cmd = f'_diffbrowsers diff -fb $fonts_before -fa $fonts_after -s $styles -o $out -pt $pt_size -ch "$characters"'
    if imgs:
        db_cmd += " --imgs"
    if filter_styles:
        db_cmd += ' --filter-styles "$filters"'
    w.rule("diffbrowsers", db_cmd)
    w.newline()

    w.comment("Run diffenator VF")
    diff_cmd = f'_diffenator $font_before $font_after -t $threshold -o $out -ch "$characters"'
    if user_wordlist:
        diff_cmd += " --user-wordlist $user_wordlist"
    diff_inst_cmd = diff_cmd + " --coords $coords"
    w.rule("diffenator", diff_cmd)
    w.rule("diffenator-inst", diff_inst_cmd)
    w.newline()

    # Setup build
    w.comment("Build rules")
    if diffbrowsers:
        diffbrowsers_out = os.path.join(out, "diffbrowsers")
        db_variables = dict(
            fonts_before=[f'"{os.path.abspath(f.ttFont.reader.file.name)}"' for f in fonts_before],
            fonts_after=[f'"{os.path.abspath(f.ttFont.reader.file.name)}"' for f in fonts_after],
            styles=styles,
            out=diffbrowsers_out,
            pt_size=pt_size,
            characters=characters,
        )
        if filter_styles:
            db_variables["filters"] = filter_styles
        w.build(diffbrowsers_out, "diffbrowsers", variables=db_variables)
    if diffenator:
        matcher = FontMatcher(fonts_before, fonts_after)
        getattr(matcher, styles)(filter_styles)
        for old_style, new_style in zip(matcher.old_styles, matcher.new_styles):
            coords = new_style.coords
            style = new_style.name.replace(" ", "-")
            diff_variables: dict[str,str] = dict(
                font_before=f'"{old_style.font.ttFont.reader.file.name}"',
                font_after=f'"{new_style.font.ttFont.reader.file.name}"',
                out=style,
                threshold=str(threshold),
                characters=characters,
            )
            if user_wordlist:
                diff_variables["user_wordlist"] = user_wordlist
            if coords:
                diff_variables["coords"] = dict_coords_to_string(coords)
                w.build(
                    os.path.join(out, style),
                    "diffenator-inst",
                    variables=diff_variables,
                )
            else:
                w.build(
                    os.path.join(out, style), "diffenator", variables=diff_variables
                )
    w.close()
    ninja._program("ninja", [])
