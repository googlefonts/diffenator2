from __future__ import annotations
import logging
import os
from ninja.ninja_syntax import Writer
from diffenator2.utils import dict_coords_to_string
from fontTools.ttLib import TTFont
import ninja
from diffenator2.utils import partition

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


MAX_STYLES = 4


def ninja_proof(
    fonts: list[TTFont],
    out: str = "out",
    imgs: bool = False,
    filter_styles: bool = None,
    pt_size: int = 20,
):
    if filter_styles:
        _ninja_proof(fonts, out, imgs, filter_styles, pt_size)
        return
    styles = styles_in_fonts(fonts)
    partitioned = partition(styles, MAX_STYLES)
    if not os.path.exists(out):
        os.mkdir(out)
    for p in partitioned:
        filter_styles = "|".join(style for _, style, _ in p)
        o = os.path.join(out, filter_styles.replace("|", "-"))
        if not os.path.exists(o):
            os.mkdir(o)
        _ninja_proof(fonts, o, imgs, filter_styles, pt_size)


def _ninja_proof(
    fonts: list[TTFont],
    out: str = "out",
    imgs: bool = False,
    filter_styles: bool = None,
    pt_size: int = 20,
):
    w = Writer(open(os.path.join("build.ninja"), "w", encoding="utf8"))
    w.comment("Rules")
    w.newline()
    out_s = os.path.join("out", "diffbrowsers")

    cmd = f"_diffbrowsers proof $fonts -o $out -pt $pt_size"
    if imgs:
        cmd += " --imgs"
    if filter_styles:
        cmd += f' --filter-styles "$filters"'
    w.rule("proofing", cmd)
    w.newline()

    # Setup build
    w.comment("Build rules")
    variables = dict(
        fonts=[os.path.abspath(f.reader.file.name) for f in fonts],
        out=out_s,
        pt_size=pt_size
    )
    if imgs:
        variables["imgs"] = imgs
    if filter_styles:
        variables["filters"] = filter_styles
    w.build(out, "proofing", variables=variables)
    w.close()
    ninja._program("ninja", [])


def ninja_diff(
    fonts_before: list[TTFont],
    fonts_after: list[TTFont],
    diffbrowsers: bool = True,
    diffenator: bool = True,
    out: str = "out",
    imgs: bool = False,
    user_wordlist: str = None,
    filter_styles: str = None,
    pt_size: int = 20,
):
    if filter_styles:
        _ninja_diff(
            fonts_before,
            fonts_after,
            diffbrowsers,
            diffenator,
            out,
            imgs,
            user_wordlist,
            filter_styles,
            pt_size,
        )
        return
    styles = styles_in_fonts(fonts_before)
    partitioned = partition(styles, MAX_STYLES)
    if not os.path.exists(out):
        os.mkdir(out)
    for p in partitioned:
        filter_styles = "|".join(style for _, style, _ in p)
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
            user_wordlist,
            filter_styles,
            pt_size,
        )

def _ninja_diff(
    fonts_before: list[TTFont],
    fonts_after: list[TTFont],
    diffbrowsers: bool = True,
    diffenator: bool = True,
    out: str = "out",
    imgs: bool = False,
    user_wordlist: str = None,
    filter_styles: str = None,
    pt_size: int = 20,
):
    w = Writer(open(os.path.join("build.ninja"), "w", encoding="utf8"))
    # Setup rules
    w.comment("Rules")
    w.newline()
    w.comment("Build Hinting docs")
    db_cmd = f"_diffbrowsers diff -fb $fonts_before -fa $fonts_after -o $out -pt $pt_size"
    if imgs:
        db_cmd += " --imgs"
    if filter_styles:
        db_cmd += ' --filter-styles "$filters"'
    w.rule("diffbrowsers", db_cmd)
    w.newline()

    w.comment("Run diffenator VF")
    diff_cmd = f"_diffenator $font_before $font_after -o $out"
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
            fonts_before=[os.path.abspath(f.reader.file.name) for f in fonts_before],
            fonts_after=[os.path.abspath(f.reader.file.name) for f in fonts_after],
            out=diffbrowsers_out,
            pt_size=pt_size
        )
        if filter_styles:
            db_variables["filters"] = filter_styles
        w.build(diffbrowsers_out, "diffbrowsers", variables=db_variables)
    if diffenator:
        for style, font_before, font_after, coords in matcher(
            fonts_before, fonts_after
        ):
            if filter_styles and style not in filter_styles:
                continue
            style = style.replace(" ", "-")
            diff_variables = dict(
                font_before=font_before,
                font_after=font_after,
                out=style,
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


def styles_in_fonts(fonts):
    styles = []
    for font in fonts:
        if "fvar" in font:
            styles += styles_in_variable_font(font)
        else:
            styles.append(style_in_static_font(font))
    return styles


def style_in_static_font(ttfont):
    return (ttfont, ttfont['name'].getBestSubFamilyName(), {})


def styles_in_variable_font(ttfont):
    assert "fvar" in ttfont
    res = []
    family_name = ttfont["name"].getBestFamilyName()
    instances = ttfont["fvar"].instances
    for inst in instances:
        name_id = inst.subfamilyNameID
        name = ttfont["name"].getName(name_id, 3, 1, 0x409).toUnicode()
        res.append((ttfont, name, inst.coordinates))
    return res


def matcher(fonts_before, fonts_after):
    before = {s: (f, s, c) for f,s,c in styles_in_fonts(fonts_before)}
    after = {s: (f, s, c) for f,s,c in styles_in_fonts(fonts_after)}
    shared = set(before.keys()) & set(after.keys())
    res = []
    for style in shared:
        res.append(
            (
                style,
                before[style][0].reader.file.name,
                after[style][0].reader.file.name,
                after[style][2]
            )
        )
    return sorted(res, key=lambda k: k[0])
