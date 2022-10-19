"""
Diffenator is primarily a visual differ. Its main job is to stop users reporting visual issues to google/fonts.

What should be checked:

- Essential tables e.g OS/2, hhea attribs (Simon seemed keen on this so discuss implementation of this in the context of what I've found here)

Output:
- A single html page. No images, just pure html and js.
"""
import logging
import os
import ninja
from ninja.ninja_syntax import Writer
from diffenator.utils import dict_coords_to_string


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def run_proofing_tools(fonts, out="out", imgs=False, filter_styles=None):
    if not os.path.exists(out):
        os.mkdir(out)

    w = Writer(open(os.path.join("build.ninja"), "w", encoding="utf8"))
    w.comment("Rules")
    w.newline()
    out_s = f"$out{os.path.sep}diffbrowsers"

    cmd = f"diffbrowsers proof $fonts -o {out_s}"
    if imgs:
        cmd += " --imgs"
    if filter_styles:
        cmd += f" --filter-styles '$filters'"
    w.rule("proofing", cmd)
    w.newline()

    # Setup build
    w.comment("Build rules")
    variables = dict(
        fonts=[f.reader.file.name for f in fonts],
        out=out,
    )
    if imgs:
        variables["imgs"] = imgs
    if filter_styles:
        variables["filters"] = filter_styles
    w.build(out, "proofing", variables=variables)
    w.close()
    ninja._program("ninja", [])


def run_diffing_tools(
    fonts_before,
    fonts_after=None,
    diffbrowsers=True,
    diffenator=True,
    out="out",
    imgs=False,
    user_wordlist=None,
    filter_styles=None,
):
    if not os.path.exists(out):
        os.mkdir(out)

    w = Writer(open(os.path.join("build.ninja"), "w", encoding="utf8"))
    # Setup rules
    w.comment("Rules")
    w.newline()
    w.comment("Build Hinting docs")
    db_cmd = f"diffbrowsers diff -fb $fonts_before -fa $fonts_after -o $out"
    if imgs:
        db_cmd += " --imgs"
    if filter_styles:
        db_cmd += " --filter-styles '$filters'"
    w.rule("diffbrowsers", db_cmd)
    w.newline()

    w.comment("Run diffenator VF")
    diff_cmd = f"diffenator $font_before $font_after -o $out"
    if user_wordlist:
        diff_cmd += " --user-wordlist $user_wordlist"
    w.rule("diffenator", diff_cmd)
    w.newline()

    # Setup build
    w.comment("Build rules")
    if diffbrowsers:
        diffbrowsers_out = os.path.join(out, "diffbrowsers")
        db_variables = dict(
            fonts_before=[
                os.path.abspath(f.reader.file.name) for f in fonts_before
            ],
            fonts_after=[os.path.abspath(f.reader.file.name) for f in fonts_after],
            out=diffbrowsers_out,
        )
        if filter_styles:
            db_variables["filters"] = filter_styles
        w.build(
            diffbrowsers_out,
            "diffbrowsers",
            variables=db_variables
        )
    if diffenator:
        for style, font_before, font_after, coords in matcher(
            fonts_before, fonts_after, filter_styles
        ):
            style = style.replace(" ", "-")
            diff_variables = dict(
                font_before=font_before,
                font_after=font_after,
                out=style,
            )
            if coords:
                diff_variables["coods"] = dict_coords_to_string(coords)
            if user_wordlist:
                diff_variables["user_wordlist"] = user_wordlist
            w.build(os.path.join(out, style), "diffenator", variables=diff_variables)
    w.close()
    ninja._program("ninja", [])


def _static_fullname(ttfont):
    return (
        f"{ttfont['name'].getBestFamilyName()} {ttfont['name'].getBestSubFamilyName()}"
    )


def _vf_fullnames(ttfont, filters=None):
    assert "fvar" in ttfont
    res = []
    family_name = ttfont["name"].getBestFamilyName()
    instances = ttfont["fvar"].instances
    for inst in instances:
        name_id = inst.subfamilyNameID
        name = ttfont["name"].getName(name_id, 3, 1, 0x409).toUnicode()
        if filters and name not in filters:
            continue
        res.append((f"{family_name} {name}", inst.coordinates))
    return res


def matcher(fonts_before, fonts_after, filters=None):
    before = {}
    after = {}
    for font in fonts_before:
        if "fvar" in font:
            vf_names = _vf_fullnames(font, filters)
            for n, coords in vf_names:
                before[n] = (os.path.abspath(font.reader.file.name), coords)
        else:
            before[_static_fullname(font)] = (
                os.path.abspath(font.reader.file.name),
                {},
            )

    for font in fonts_after:
        if "fvar" in font:
            vf_names = _vf_fullnames(font, filters)
            for n, coords in vf_names:
                after[n] = (os.path.abspath(font.reader.file.name), coords)
        else:
            after[_static_fullname(font)] = (os.path.abspath(font.reader.file.name), {})

    shared = set(before.keys()) & set(after.keys())
    res = []
    for style in shared:
        res.append((style, before[style][0], after[style][0], after[style][1]))
    return res
