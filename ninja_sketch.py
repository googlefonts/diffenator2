from ninja.ninja_syntax import Writer
import ninja
import argparse
import os
from fontTools.ttLib import TTFont


def _fullname(ttfont):
    return f"{ttfont['name'].getBestFamilyName()} {ttfont['name'].getBestSubFamilyName()}"


def _vf_fullnames(ttfont):
    assert "fvar" in ttfont
    res = []
    family_name = ttfont['name'].getBestFamilyName()
    instances = ttfont["fvar"].instances
    for inst in instances:
        name_id = inst.subfamilyNameID
        name = ttfont['name'].getName(name_id, 3, 1, 0x409).toUnicode()
        res.append((f"{family_name} {name}", inst.coordinates))
    return res


def matcher(fonts_before, fonts_after):
    before = {}
    after = {}
    for font in fonts_before:
        if "fvar" in font:
            vf_names = _vf_fullnames(font)
            for n, coords in vf_names:
                before[n] = (font.reader.file.name, coords)
        else:
            before[_fullname(font)] = (font.reader.file.name, {})
    
    for font in fonts_after:
        if "fvar" in font:
            vf_names = _vf_fullnames(font)
            for n, coords in vf_names:
                after[n] = (font.reader.file.name, coords)
        else:
            after[_fullname(font)] = (font.reader.file.name, {})
    
    shared = set(before.keys()) & set(after.keys())
    res = []
    for style in shared:
        res.append((style, before[style][0], after[style][0], after[style][1]))
    return res


def dict_coords_to_string(coords):
    return ",".join(f"{k}={v}" for k,v in coords.items())


parser = argparse.ArgumentParser()
parser.add_argument("--fonts-before", "-fb", nargs="+", required=True)
parser.add_argument("--fonts-after", "-fa", nargs="+", required=True)
parser.add_argument("--out", "-o", default="outer")
args = parser.parse_args()

fonts_before = [TTFont(f) for f in args.fonts_before]
fonts_after = [TTFont(f) for f in args.fonts_after]

if not os.path.exists(args.out):
    os.mkdir(args.out)

# TODO tempfile this
w = Writer(open("build.ninja", "w"))
# Setup rules
w.comment("Rules")
w.newline()
w.comment("Build Hinting docs")
w.rule("diffbrowsers", "diffbrowsers diff -fb $fonts_before -fa $fonts_after -o $out/diffbrowsers")
w.newline()

# TODO match fonts and call this multiple times!
w.comment("Run diffenator")
w.rule("diffenator", "diffenator $font_before $font_after -c $coords -o $out")
w.newline()
w.newline()

# Setup build
w.comment("Build rules")
w.build(args.out, "diffbrowsers", variables=dict(
    fonts_before=args.fonts_before,
    fonts_after=args.fonts_after,
    out=args.out,
))
for style, font_before, font_after, coords in matcher(fonts_before, fonts_after):
    style = style.replace(" ", "-")
    w.build(
        os.path.join(args.out, style), "diffenator", variables=dict(
            font_before=font_before,
            font_after=font_after,
            coords=dict_coords_to_string(coords),
            out=style
        ))
w.close()

# Run
ninja._program("ninja", [])
