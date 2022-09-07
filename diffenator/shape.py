"""
Check fonts for shaping regressions using real words.
"""
from diffenator.font import DFont
from dataclasses import dataclass
from lxml import etree
from lxml import objectify
from collections import defaultdict
import uharfbuzz as hb
import argparse
from string import Template
import os
import shutil
import tempfile
from blackrenderer.render import renderText
from PIL import Image
from pkg_resources import resource_filename
import ahocorasick


TEMPLATE = Template(
    """
<html>
    <head>
        <style>
            @font-face {
                font-family: "font_a";
                src: url("$font_a");
            }
            @font-face {
                font-family: "font_b";
                src: url("$font_b");
            }
            .before{
                color: green;
                font-size: 32pt;
                font-family: font_a;
            }
            .after{
                color: red;
                font-size: 32pt;
                font-family: font_b;
            }
            .left{
                float: left;
                width: 40%;
            }
            .right{
                float: left;
                width:40%;
            }
        </style>
    </head>
    <body>
        <div style="float=left, margin-bottom=32pt"><b>Missing glyphs:</b></div>
        <div>
            $missing_glyphs
        </div>
        <div style="float=left, margin-bottom=32pt"><b>New glyphs:</b></div>
        <div class="after">
            $new_glyphs
        </div>
        <div style="float=left, margin-bottom=32pt"><b>Modified glyphs:</b></div>
        <div class="left before">
            $modified_glyphs
        </div>
        <div class="right after">
            $modified_glyphs
        </div>
        <div style="float=left, margin-bottom=32pt"><b>Following words have different shaping or pixels differences over threshold:</b></div>
        <div class="left before">
            $text
        </div>
        <div class="right after">
            $text
        </div>
    </body>
</html>
"""
)


def remove_substring_words(words):
    res = set()
    auto = ahocorasick.Automaton()
    for word in words:
        auto.add_word(word, word)
        res.add(word)
    auto.make_automaton()

    for word in words:
        for end_ind, found in auto.iter(word):
            if word != found:
                try:
                    res.remove(found)
                except:
                    all
    return res


def build_words(fp, out, keep_chars=None):
    root = objectify.parse(fp).getroot()
    bank = set()
    word_freq = defaultdict(int)
    for page in root.page:
        page_text = etree.tostring(page.revision, encoding="unicode")
        words = page_text.split()
        for word in words:
            word_freq[word] += 1
            if keep_chars and all(c in keep_chars for c in word):
                bank.add(word)
    
    words = remove_substring_words(bank)
    # Remove pairs which have already been seen
    res = set()
    for word in words:
        if word_freq[word] <= 2:
            continue
        res.add(word)
    with open(out, "w") as doc:
        doc.write("\n".join(res))


def test_words(
    word_file, font_a, font_b, skip_glyphs=set(), diff_pixels=False
):
    seen_a, seen_b = defaultdict(set), defaultdict(set)
    seen_codepoints = set()
    with open(word_file) as doc:
        words = doc.read().split("\n")
        print(f"testing {len(words)} words")
        for i, word in enumerate(words):
            if any(c in word for c in skip_glyphs):
                continue
            buf_a = hb.Buffer()
            buf_a.add_str(word)
            buf_a.guess_segment_properties()
            hb.shape(font_a.hbFont, buf_a)

            infos_a = buf_a.glyph_infos
            pos_a = buf_a.glyph_positions

            buf_b = hb.Buffer()
            buf_b.add_str(word)
            buf_b.guess_segment_properties()
            hb.shape(font_b.hbFont, buf_b)

            infos_b = buf_b.glyph_infos
            pos_b = buf_b.glyph_positions

            for info, pos in zip(infos_a, pos_a):
                seen_a[(info.codepoint, pos.position)].add(word)
            for info, pos in zip(infos_b, pos_b):
                seen_b[(info.codepoint, pos.position)].add(word)

    res = set()
    missing = set(seen_a) - set(seen_b)
    if missing:
        for m in missing:
            res |= set(list(seen_a[m])[:100])

    shared = set(seen_a) & set(seen_b)
    for idx in shared:
        words_a = seen_a[idx]
        words_b = seen_b[idx]
        missing = words_a - words_b
        if missing:
            res |= missing

    if diff_pixels:
        print(f"Pixel diffing results. This may take a while.")
        res = px_diff(font_a, font_b, res)
    return res


def px_diff(font_a, font_b, strings, thresh=0.000000005):
    res = []
    quant = len(strings)
    print(f"px diffing {quant}")
    for idx, string in enumerate(strings):
        print(f"{idx}/{quant}")
        with tempfile.NamedTemporaryFile(
            suffix=".png"
        ) as out_a, tempfile.NamedTemporaryFile(suffix=".png") as out_b:
            try:
                renderText(font_a.path, string, out_a.name, fontSize=12, margin=0)
                renderText(font_b.path, string, out_b.name, fontSize=12, margin=0)
                img_a = Image.open(out_a.name)
                img_b = Image.open(out_b.name)
                width = min([img_a.width, img_b.width])
                height = min([img_a.height, img_b.height])
                diff_pixels = 0
                for x in range(width):
                    for y in range(height):
                        px_a = img_a.getpixel((x, y)) 
                        px_b = img_b.getpixel((x, y))
                        if px_a != px_b:
                            diff_pixels += abs(px_a[0] - px_b[0])
                            diff_pixels += abs(px_a[1] - px_b[1])
                            diff_pixels += abs(px_a[2] - px_b[2])
                            diff_pixels += abs(px_a[3] - px_b[3])
                pc = diff_pixels / (width * height * 255 * 255 * 255 * 255)
                if pc > thresh:
                    res.append((pc, string))
            except:
                all
    print("done")
    return [i[1] for i in sorted(res, key=lambda k: k[0], reverse=True)]


@dataclass
class GlyphDiff:
    missing: list
    new: list
    modified: list


def test_fonts(font_a, font_b, diff_pixels=True):
    glyphs = test_font_glyphs(font_a, font_b, diff_pixels=diff_pixels)
    skip_glyphs = glyphs.missing + glyphs.new
    words = test_font_words(font_a, font_b, skip_glyphs, diff_pixels=diff_pixels)
    return {"glyphs": glyphs, "words": words}


def test_font_glyphs(font_a, font_b, diff_pixels=True):
    cmap_a = set(
        chr(c)
        for c in font_a.ttFont.getBestCmap()
        if c not in list(range(33)) + [847, 8288, 8203, 160, 6068, 6069, 173, 8204, 8205]
    )
    cmap_b = set(
        chr(c)
        for c in font_b.ttFont.getBestCmap()
        if c not in list(range(33)) + [847, 8288, 8203, 160, 6068, 6069, 173, 8204, 8205]
    )
    missing_glyphs = cmap_a - cmap_b
    new_glyphs = cmap_b - cmap_a
    same_glyphs = cmap_a & cmap_b
    skip_glyphs = missing_glyphs | new_glyphs
    modified_glyphs = px_diff(font_a, font_b, list(same_glyphs))

    return GlyphDiff(
        list(sorted(missing_glyphs)),
        list(sorted(new_glyphs)),
        list(sorted(modified_glyphs)),
    )


def test_font_words(font_a, font_b, skip_glyphs=set(),diff_pixels=True):
    from youseedee import ucd_data
    from collections import defaultdict
    scripts = defaultdict(int)
    cmap_a = font_a.ttFont.getBestCmap()
    for k in cmap_a:
        data = ucd_data(k)
        try:
            scripts[data["Script"]] += 1
        except:
            continue

    res = {}
    for script, count in scripts.items():
        if count < 10:
            continue
        wordlist = resource_filename("diffenator", f"data/wordlists/{script}.txt")
        if not os.path.exists(wordlist):
            print(f"No wordlist for {script}")
            continue
        res[script] = test_words(wordlist, font_a, font_b, skip_glyphs=skip_glyphs, diff_pixels=True)
    return res


def gen_report(font_a, font_b, data, out):
    if os.path.exists(out):
        shutil.rmtree(out)
    os.mkdir(out)
    html_fp = os.path.join(out, "index.html")
    shutil.copy(font_a.fp, out)
    shutil.copy(font_b.fp, out)
    with open(html_fp, "w") as doc:
        doc.write(
            TEMPLATE.substitute(
                font_a=os.path.basename(font_a.fp),
                font_b=os.path.basename(font_b.fp),
                missing_glyphs=" ".join(data["glyphs"].missing),
                new_glyphs=" ".join(data["glyphs"].new),
                modified_glyphs="<br>\n".join(data["glyphs"].modified),
                text="<br>\n".join(data.mishaped_words),
            )
        )


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True, dest="cmd")

    build = subparsers.add_parser("build")
    build.add_argument("xml_fp")
    build.add_argument("out")
    build.add_argument("--glyphs", "-g", default=None)

    test = subparsers.add_parser("test")
    test.add_argument("word_file")
    test.add_argument("font_a")
    test.add_argument("font_b")
    test.add_argument("--out", "-o", default="out")
    test.add_argument("--px-diff", "-px", action="store_true", default=False)

    args = parser.parse_args()

    if args.cmd == "test":
        font_a = DFont(args.font_a)
        font_b = DFont(args.font_b)
        data = test_fonts(args.word_file, font_a, font_b, args.px_diff)
        gen_report(font_a, font_b, data, args.out)

    elif args.cmd == "build":
        glyphs = None if not args.glyphs else set(args.glyphs)
        build_words(args.xml_fp, args.out, glyphs)


if __name__ == "__main__":
    main()
