"""
Check fonts for shaping regressions using real words.
"""
import unicodedata2 as uni
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
from jinja2 import pass_environment


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


def gid_pos_hash(info, pos):
    return f"gid={info.codepoint}, pos={pos.position}<br>"


def gid_hash(info, _):
    return f"gid={info.codepoint}"


def test_words(word_file, font_a, font_b, skip_glyphs=set(), hash_func=gid_pos_hash):
    res = set()
    with open(word_file) as doc:
        words = doc.read().split("\n")
        print(f"testing {len(words)} words")
        word_total = len(words)
        for i, line in enumerate(words):
            items = line.split(",")
            word, features = items[0], items[1:]
            features = {k: True for k in features}
            print(i, word_total)
            if any(c.string in word for c in skip_glyphs):
                continue
            
            buf_a = hb.Buffer()
            buf_a.add_str(word)
            buf_a.guess_segment_properties()
            hb.shape(font_a.hbFont, buf_a, features=features)

            infos_a = buf_a.glyph_infos
            pos_a = buf_a.glyph_positions
            hb_a = "".join(hash_func(i, j) for i,j in zip(infos_a, pos_a))
            word_a = Word(word, hb_a)

            buf_b = hb.Buffer()
            buf_b.add_str(word)
            buf_b.guess_segment_properties()
            hb.shape(font_b.hbFont, buf_b, features=features)

            infos_b = buf_b.glyph_infos
            pos_b = buf_b.glyph_positions
            hb_b = "".join(hash_func(i, j) for i,j in zip(infos_b, pos_b))
            word_b = Word(word, hb_b)

            if word_a != word_b:
                pc = px_diff2(font_a, font_b, word, features=features)
                if pc >= 0.004:
                    res.add((pc, WordDiff(word, word_a.hb, word_b.hb, tuple(features.keys()))))
    return [w[1] for w in sorted(res, key=lambda k: k[0], reverse=True)]


class Renderable:
    @pass_environment
    def render(self, jinja):
        classname = self.__class__.__name__
        template = jinja.get_template(f"{classname}.partial.html")
        return template.render(self.__dict__)


@dataclass
class Word:
    string: str
    hb: str

    def __eq__(self, other):
        return (self.string, hb) == (other.string, other.hb)
    
    def __hash__(self):
        return hash((self.string, self.hb))


@dataclass
class WordDiff(Renderable):
    string: str
    hb_a: str
    hb_b: str
    ot_features: tuple

    def __hash__(self):
        return hash((self.string, self.hb_a, self.hb_b, self.ot_features))



def px_diff(font_a, font_b, strings, thresh=0.00005):
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
                pc = diff_pixels / (width * height * 256 * 3 * 3 * 3)
                if pc > thresh:
                    res.append((pc, string))
            except:
                all
    print("done")
    s = [i[1] for i in sorted(res, key=lambda k: k[0], reverse=True)]
    return s


def px_diff2(font_a, font_b, string, features=None):
    pc = 0.0
    with tempfile.NamedTemporaryFile(
        suffix=".png"
    ) as out_a, tempfile.NamedTemporaryFile(suffix=".png") as out_b:
        try:
            renderText(font_a.path, string, out_a.name, fontSize=12, margin=0, features=features)
            renderText(font_b.path, string, out_b.name, fontSize=12, margin=0, features=features)
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
            pc = diff_pixels / (width * height * 256 * 3 * 3 * 3)
        except:
            all
    return pc


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
    )
    cmap_b = set(
        chr(c)
        for c in font_b.ttFont.getBestCmap()
    )
    missing_glyphs = set(Glyph(c, uni.name(c), ord(c)) for c in cmap_a - cmap_b)
    new_glyphs = set(Glyph(c, uni.name(c), ord(c)) for c in cmap_b - cmap_a)
    same_glyphs = cmap_a & cmap_b
    skip_glyphs = missing_glyphs | new_glyphs
    modified_glyphs = []
    for g in same_glyphs:
        pc = px_diff2(font_a, font_b, g)
        if pc > 0.0005:
            glyph = GlyphD(g, uni.name(g), ord(g), pc)
            modified_glyphs.append(glyph)
    modified_glyphs.sort(key=lambda k: k.changed_pixels, reverse=True)

    return GlyphDiff(
        list(sorted(missing_glyphs, key=lambda k: k.string)),
        list(sorted(new_glyphs, key=lambda k: k.string)),
        modified_glyphs,
    )


@dataclass
class Glyph(Renderable):
    string: str
    name: str
    unicode: str

    def __hash__(self):
        return hash((self.string, self.name, self.unicode))


@dataclass
class GlyphD(Renderable):
    string: str
    name: str
    unicode: str
    changed_pixels: float

    def __hash__(self):
        return hash((self.string, self.name, self.unicode))



def test_font_words(font_a, font_b, skip_glyphs=set(), diff_pixels=True):
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
        res[script] = test_words(
            wordlist, font_a, font_b, skip_glyphs=skip_glyphs
        )
    return res
