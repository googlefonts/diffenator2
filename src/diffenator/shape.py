"""
Check fonts for shaping regressions using real words.
"""
from __future__ import annotations
import unicodedata2 as uni
from dataclasses import dataclass
from lxml import etree
from lxml import objectify
import uharfbuzz as hb
import os
from diffenator.renderer import Renderer
from pkg_resources import resource_filename
from jinja2 import pass_environment
from threading import Thread


THRESHOLD = 0.000002

# Functions to test word lists


ot_to_html_lang = {
    (None, None): "en",
    ("latn", "dflt"): "en",
    ("arab", "ARA"): "ar",
    ("dev2", "HIN"): "hi",
    ("dev2", "MAR"): "mr",
    ("dev2", "NEP"): "ne",
    ("latn", "MOL"): "mo",
    ("cyrl", "SRB"): "sr",
}

ot_to_dir = {None: "ltr", "arab": "rlt", "hebr": "rtl"}


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
    lang: str
    direction: str
    diff_map: list[int]

    def __hash__(self):
        return hash((self.string, self.hb_a, self.hb_b, self.ot_features))


@dataclass
class Glyph(Renderable):
    string: str
    name: str
    unicode: str

    def __hash__(self):
        return hash((self.string, self.name, self.unicode))


@dataclass
class GlyphDiff(Renderable):
    string: str
    name: str
    unicode: str
    changed_pixels: float
    diff_map: list[int]

    def __hash__(self):
        return hash((self.string, self.name, self.unicode))


@dataclass
class GlyphItems:
    missing: list
    new: list
    modified: list


def gid_pos_hash(info, pos):
    return f"gid={info.codepoint}, pos={pos.position}<br>"


def gid_hash(info, _):
    return f"gid={info.codepoint}<br>"


def test_fonts(font_a, font_b):
    glyphs = test_font_glyphs(font_a, font_b)
    skip_glyphs = glyphs.missing + glyphs.new
    words = test_font_words(font_a, font_b, skip_glyphs)
    return {"glyphs": glyphs, "words": words}


def test_font_glyphs(font_a, font_b):
    cmap_a = set(chr(c) for c in font_a.ttFont.getBestCmap())
    cmap_b = set(chr(c) for c in font_b.ttFont.getBestCmap())
    missing_glyphs = set(Glyph(c, uni.name(c), ord(c)) for c in cmap_a - cmap_b)
    new_glyphs = set(Glyph(c, uni.name(c), ord(c)) for c in cmap_b - cmap_a)
    same_glyphs = cmap_a & cmap_b
    skip_glyphs = missing_glyphs | new_glyphs
    modified_glyphs = []
    differ = PixelDiffer(font_a, font_b)
    for g in same_glyphs:
        pc, diff_map = differ.diff(g)
        if pc > THRESHOLD:
            try:
                uni_name = uni.name(g)
            except ValueError:
                uni_name = ""
            glyph = GlyphDiff(g, uni_name, ord(g), pc, diff_map)
            modified_glyphs.append(glyph)
    modified_glyphs.sort(key=lambda k: k.changed_pixels, reverse=True)

    return GlyphItems(
        list(sorted(missing_glyphs, key=lambda k: k.string)),
        list(sorted(new_glyphs, key=lambda k: k.string)),
        modified_glyphs,
    )


def test_font_words(font_a, font_b, skip_glyphs=set()):
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
        res[script] = test_words(wordlist, font_a, font_b, skip_glyphs)
    return res


def test_words(
    word_file,
    font_a,
    font_b,
    skip_glyphs=set(),
    hash_func=gid_pos_hash,
    threshold=THRESHOLD,
):
    res = set()
    from collections import defaultdict

    seen_gids = defaultdict(int)

    differ = PixelDiffer(font_a, font_b)
    with open(word_file, encoding="utf8") as doc:
        words = doc.read().split("\n")
        print(f"testing {len(words)} words")
        word_total = len(words)
        for i, line in enumerate(words):
            skip_px = False
            items = line.split(",")
            try:
                word, script, lang, features = items[0], items[1], items[2], items[3:]
            # for wordlists which just contain words
            except IndexError:
                word, script, lang, features = items[0], None, None, []
            features = {k: True for k in features}
            if any(c.string in word for c in skip_glyphs):
                continue

            differ.set_script(script)
            differ.set_lang(lang)
            differ.set_features(features)

            buf_a = differ.renderer_a.shape(word)
            buf_b = differ.renderer_b.shape(word)

            infos_a = buf_a.glyph_infos
            pos_a = buf_a.glyph_positions
            hb_a = "".join(hash_func(i, j) for i, j in zip(infos_a, pos_a))
            word_a = Word(word, hb_a)

            infos_b = buf_b.glyph_infos
            pos_b = buf_b.glyph_positions
            hb_b = "".join(hash_func(i, j) for i, j in zip(infos_b, pos_b))
            word_b = Word(word, hb_b)

            if all(seen_gids[hash_func(i, j)] >= 1 for i, j in zip(infos_b, pos_b)):
                continue

            pc, diff_map = differ.diff(word)

            if pc >= threshold:
                for i, j in zip(infos_b, pos_b):
                    h = hash_func(i, j)
                    seen_gids[h] += 1
                res.add(
                    (
                        pc,
                        WordDiff(
                            word,
                            word_a.hb,
                            word_b.hb,
                            tuple(features.keys()),
                            ot_to_html_lang.get((script, lang)),
                            ot_to_dir.get(script, None),
                            diff_map,
                        ),
                    )
                )
    return [w[1] for w in sorted(res, key=lambda k: k[0], reverse=True)]


@dataclass
class PixelDiffer:
    font_a: DFont
    font_b: DFont
    script=None
    lang=None
    features=None

    def __post_init__(self):
        self.renderer_a = Renderer(
            self.font_a,
            font_size=3,
            margin=0,
            features=self.features,
            script=self.script,
            lang=self.lang,
            variations=getattr(self.font_a, "variations", None)
        )
        self.renderer_b = Renderer(
            self.font_b,
            font_size=3,
            margin=0,
            features=self.features,
            script=self.script,
            lang=self.lang,
            variations=getattr(self.font_b, "variations", None)
        )

    def set_script(self, script):
        self.renderer_a.script = script
        self.renderer_b.script = script

    def set_lang(self, lang):
        self.renderer_a.lang = lang
        self.renderer_b.lang = lang

    def set_features(self, features):
        self.renderer_a.features = features
        self.renderer_b.features = features

    def diff(self, string):
        pc = 0.0
        img_a = self.renderer_a.render(string)
        img_b = self.renderer_b.render(string)
        width = min([img_a.width, img_b.width])
        height = min([img_a.height, img_b.height])
        diff_pixels = 0
        diff_map = []
        for x in range(width):
            for y in range(height):
                px_a = img_a.getpixel((x, y))
                px_b = img_b.getpixel((x, y))
                if px_a != px_b:
                    if isinstance(px_a, int) and isinstance(px_b, int):
                        diff_pixel = abs(px_a - px_b)
                        diff_pixels += diff_pixel
                        diff_map.append(diff_pixel)
                    else:
                        diff_pixel += abs(px_a[0] - px_b[0])
                        diff_pixel += abs(px_a[1] - px_b[1])
                        diff_pixel += abs(px_a[2] - px_b[2])
                        diff_pixel += abs(px_a[3] - px_b[3])
                        diff_pixels += diff_pixel
                        diff_map.append(diff_pixel)
                else:
                    diff_map.append(0)
        try:
            pc = diff_pixels / (width * height * 256 * 4)
        except ZeroDivisionError:
            pc = 0
        return pc, diff_map
