"""
Check fonts for shaping regressions using real words.
"""
from __future__ import annotations
from dataclasses import dataclass
import uharfbuzz as hb
import os
from diffenator2 import THRESHOLD
from diffenator2.renderer import PixelDiffer
from diffenator2.template_elements import WordDiff, Glyph, GlyphDiff
from pkg_resources import resource_filename
import tqdm
from diffenator2.segmenting import textSegments


# Hashing strategies for elements of a Harfbuzz buffer

def gid_pos_hash(info, pos):
    return f"gid={info.codepoint}, pos={pos.position}<br>"


# def gid_hash(info, _):
#     return f"gid={info.codepoint}<br>"


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


@dataclass
class Word:
    string: str
    hb: str

    @classmethod
    def from_buffer(cls, word, buffer, hash_func=gid_pos_hash):
        infos = buffer.glyph_infos
        pos = buffer.glyph_positions
        hb = "".join(hash_func(i, j) for i, j in zip(infos, pos))
        return cls(word, hb)

    def __eq__(self, other):
        return (self.string, hb) == (other.string, other.hb)

    def __hash__(self):
        return hash((self.string, self.hb))


@dataclass
class GlyphItems:
    missing: list
    new: list
    modified: list


def test_fonts(font_a, font_b, threshold=THRESHOLD):
    glyphs = test_font_glyphs(font_a, font_b, threshold=threshold)
    skip_glyphs = glyphs.missing + glyphs.new
    words = test_font_words(font_a, font_b, skip_glyphs, threshold=threshold)
    return {"glyphs": glyphs, "words": words}


def test_font_glyphs(font_a, font_b, threshold=THRESHOLD):
    cmap_a = set(chr(c) for c in font_a.ttFont.getBestCmap())
    cmap_b = set(chr(c) for c in font_b.ttFont.getBestCmap())
    missing_glyphs = set(Glyph(c) for c in cmap_a - cmap_b)
    new_glyphs = set(Glyph(c) for c in cmap_b - cmap_a)
    same_glyphs = cmap_a & cmap_b
    skip_glyphs = missing_glyphs | new_glyphs
    modified_glyphs = []
    differ = PixelDiffer(font_a, font_b)
    for g in same_glyphs:
        pc, diff_map = differ.diff(g)
        if pc > threshold:
            glyph = GlyphDiff(g, "%.2f" % pc, diff_map)
            modified_glyphs.append(glyph)
    modified_glyphs.sort(key=lambda k: k.changed_pixels, reverse=True)

    return GlyphItems(
        list(sorted(missing_glyphs, key=lambda k: k.string)),
        list(sorted(new_glyphs, key=lambda k: k.string)),
        modified_glyphs,
    )


def test_font_words(font_a, font_b, skip_glyphs=set(), threshold=THRESHOLD):
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
        wordlist = resource_filename("diffenator2", f"data/wordlists/{script}.txt")
        if not os.path.exists(wordlist):
            print(f"No wordlist for {script}")
            continue
        res[script] = test_words(wordlist, font_a, font_b, skip_glyphs, threshold=threshold)
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
        sentences = doc.read().split("\n")
        print(f"testing {len(sentences)} words")
        word_total = len(sentences)
        for i, line in tqdm.tqdm(enumerate(sentences), total=word_total):
            items = line.split(",")
            try:
                sentence, script, lang, features = items[0], items[1], items[2], items[3:]
            # for wordlists which just contain sentences
            except IndexError:
                sentence, script, lang, features = items[0], "dflt", None, []
            features = {k: True for k in features}

            differ.set_script(script)
            differ.set_lang(lang)
            differ.set_features(features)

            # split sentences into individual script segments. This mimmics the
            # same behaviour as dtp apps, web browsers etc
            for segment, script, _, _, in textSegments(sentence)[0]:

                if any(c.string in segment for c in skip_glyphs):
                    continue

                if not segment:
                    continue

                buf_b = differ.renderer_b.shape(segment)
                word_b = Word.from_buffer(segment, buf_b)

                gid_hashes = [hash_func(i, j) for i, j in zip(buf_b.glyph_infos, buf_b.glyph_positions)]
                # I'm not entirely convinced this is a valid test; but it seems to
                # work and speeds things up a lot...
                if all(gid_hash in seen_gids for gid_hash in gid_hashes):
                    continue

                buf_a = differ.renderer_a.shape(segment)
                word_a = Word.from_buffer(segment, buf_a)

                # skip any words which cannot be shaped correctly
                if any([g.codepoint == 0 for g in buf_a.glyph_infos+buf_b.glyph_infos]):
                    continue

                pc, diff_map = differ.diff(segment)

                for gid_hash in gid_hashes:
                    seen_gids[gid_hash] = True

                    if pc < threshold:
                        continue
                    res.add(
                        (
                            pc,
                            WordDiff(
                                sentence,
                                word_a.hb,
                                word_b.hb,
                                tuple(features.keys()),
                                ot_to_html_lang.get((script, lang)),
                                ot_to_dir.get(script, None),
                                "%.2f" % pc,
                            ),
                        )
                    )
    return [w[1] for w in sorted(res, key=lambda k: k[0], reverse=True)]

