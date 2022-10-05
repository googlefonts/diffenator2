"""
Diffenator is primarily a visual differ. Its main job is to stop users reporting visual issues to google/fonts.

What should be checked:

- Essential tables e.g OS/2, hhea attribs (Simon seemed keen on this so discuss implementation of this in the context of what I've found here)

Output:
- A single html page. No images, just pure html and js.
"""
import logging
import os
import tempfile
import ninja
from ninja.ninja_syntax import Writer


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def dict_coords_to_string(coords):
    return ",".join(f"{k}={v}" for k, v in coords.items())


def string_coords_to_dict(string):
    if not string:
        return {}
    return  {s.split("=")[0]: float(s.split("=")[1]) for s in string.split(",")}



def run_proofing_tools(fonts, out="out", imgs=True):
    if not os.path.exists(out):
        os.mkdir(out)

    with tempfile.TemporaryDirectory() as dir_:
        w = Writer(open(os.path.join(dir_, "build.ninja"), "w"))
        w.comment("Rules")
        w.newline()
        out_s = f"$out{os.path.sep}diffbrowsers"

        if imgs:
            cmd = f"diffbrowsers proof $fonts --imgs -o {out_s}"
        else:
            cmd = f"diffbrowsers proof $fonts -o {out_s}"
        w.rule("proofing", cmd)
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
        cwd = os.getcwd()
        os.chdir(dir_)
        ninja._program("ninja", [])
        os.chdir(cwd)


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
        if imgs:
            cmd = f"diffbrowsers diff -fb $fonts_before -fa $fonts_after --imgs -o $out"
        else:
            cmd = f"diffbrowsers diff -fb $fonts_before -fa $fonts_after -o $out"
        w.rule(
            "diffbrowsers",
            cmd,
        )
        w.newline()

        w.comment("Run diffenator")
        w.rule("diffenator", "diffenator $font_before $font_after -c $coords -o $out")
        w.newline()

        # Setup build
        w.comment("Build rules")
        if diffbrowsers:
            diffbrowsers_out = os.path.join(out, "diffbrowsers")
            w.build(
                diffbrowsers_out,
                "diffbrowsers",
                variables=dict(
                    fonts_before=[os.path.abspath(f.reader.file.name) for f in fonts_before],
                    fonts_after=[os.path.abspath(f.reader.file.name) for f in fonts_after],
                    out=diffbrowsers_out,
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
        cwd = os.getcwd()
        os.chdir(dir_)
        ninja._program("ninja", [])
        os.chdir(cwd)


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
