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


class Trie:
    def __init__(self):
        self.root = {"": {}}
        self.words = []
    
    def add_word(self, word):
        head = self.root[""]
        for c in word:
            if c not in head:
                head[c] = {}
            head = head[c]
    
    def find_words(self):
        self._get(self.root, "", "")
    
    def _get(self, data, k, word):
        for c in data[k]:
            if not data[k][c]:
                self.words.append(word+c)
            self._get(data[k], c, word+c)


def build_words(fp, out, keep_chars=None):
    root = objectify.parse(fp).getroot()
    bank = set()
    for page in root.page:
        page_text = etree.tostring(page.revision, encoding="unicode")
        words = page_text.split()
        for word in words:
            if keep_chars and all(c in keep_chars for c in word):
                bank.add(word)
    
    # Remove sub words
    t = Trie()
    for word in bank:
        t.add_word(word)
    t.find_words()
    with open(out, "w") as doc:
        doc.write("\n".join(t.words))


def test_words(
    word_file, font_a, font_b, skip_glyphs=set(), diff_pixels=False
):
    seen_a, seen_b = defaultdict(set), defaultdict(set)
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
            for info, pos in zip(infos_a, pos_a):
                seen_a[(info.codepoint, pos.position)].add(word)

            buf_b = hb.Buffer()
            buf_b.add_str(word)
            buf_b.guess_segment_properties()
            hb.shape(font_b.hbFont, buf_b)

            infos_b = buf_b.glyph_infos
            pos_b = buf_b.glyph_positions
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
            res |= set(list(missing)[:100])

    if diff_pixels:
        print(f"Pixel diffing results. This may take a while.")
        res = px_diff(font_a, font_b, res)
    return res


def px_diff(font_a, font_b, strings, thresh=0.02):
    res = []
    quant = len(strings)
    print(f"px diffing {quant}")
    for idx, string in enumerate(strings):
        print(f"{idx}/{quant}")
        with tempfile.NamedTemporaryFile(
            suffix=".png"
        ) as out_a, tempfile.NamedTemporaryFile(suffix=".png") as out_b:
            renderText(font_a.path, string, out_a.name, fontSize=12, margin=0)
            renderText(font_b.path, string, out_b.name, fontSize=12, margin=0)
            img_a = Image.open(out_a.name)
            img_b = Image.open(out_b.name)
            width = min([img_a.width, img_b.width])
            height = min([img_a.height, img_b.height])
            diff_pixels = 0
            for x in range(width):
                for y in range(height):
                    if img_a.getpixel((x, y)) != img_b.getpixel((x, y)):
                        diff_pixels += 1
            if diff_pixels / (width * height) > thresh:
                res.append(string)
    print("done")
    return res


@dataclass
class GlyphDiff:
    missing: list
    new: list
    modified: list
    mishaped_words: list


def test_fonts(word_file, font_a, font_b, diff_pixels=False):
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

    badly_shaped = test_words(word_file, font_a, font_b, skip_glyphs, diff_pixels)

    return GlyphDiff(
        list(sorted(missing_glyphs)),
        list(sorted(new_glyphs)),
        list(sorted(modified_glyphs)),
        sorted(badly_shaped),
    )


def test_shaping(font_a, font_b):
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
        res[script] = test_fonts(wordlist, font_a, font_b, diff_pixels=True)
    return res


def gen_report(font_a, font_b, glyph_diff, out):
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
                missing_glyphs=" ".join(glyph_diff.missing),
                new_glyphs=" ".join(glyph_diff.new),
                modified_glyphs="<br>\n".join(glyph_diff.modified),
                text="<br>\n".join(glyph_diff.mishaped_words),
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
        glyph_diff = test_fonts(args.word_file, font_a, font_b, args.px_diff)
        gen_report(font_a, font_b, glyph_diff, args.out)

    elif args.cmd == "build":
        glyphs = None if not args.glyphs else set(args.glyphs)
        build_words(args.xml_fp, args.out, glyphs)


if __name__ == "__main__":
    main()
