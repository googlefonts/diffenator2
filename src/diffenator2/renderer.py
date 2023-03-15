from __future__ import annotations
import argparse
import logging
import uharfbuzz as hb
from blackrenderer.render import (
    buildGlyphLine,
    scaleRect,
    insetRect,
    calcGlyphLineBounds,
    intRect,
)
from blackrenderer.backends import getSurfaceClass
from PIL import Image
from diffenator2.font import DFont
import numpy as np
import freetype as ft
from dataclasses import dataclass, field

FONT_SIZE = 28

logger = logging.getLogger(__name__)


@dataclass
class Renderer:
    font: DFont
    font_size: int=250
    margin: int=20
    features: dict[str, bool] = None
    variations: dict[str, float] = None
    lang: str = None
    script: str = None
    cache: dict[int,any] = field(default_factory=dict)


    def shape(self, text):
        hb_font = self.font.hbFont
        if self.variations:
            hb_font.set_variations(self.variations)
        hb.ot_font_set_funcs(hb_font)

        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()

        if self.script:
            buf.script = self.script
        if self.lang:
            buf.language = self.lang

        hb.shape(hb_font, buf, self.features)
        return buf

    def render(self, text):
        # See render_text_ft below
        return self.render_text_cairo(text)

    def render_text_cairo(self, text):
        font = self.font.blackFont
        glyphNames = font.glyphNames

        scaleFactor = self.font_size / font.unitsPerEm
        if self.variations:
            font.setLocation(self.variations)

        buf = self.shape(text)

        infos = buf.glyph_infos
        positions = buf.glyph_positions
        glyphLine = buildGlyphLine(infos, positions, glyphNames)
        orig_bounds = calcGlyphLineBounds(glyphLine, font)
        extents = self.font.hbFont.get_font_extents(buf.direction)
        # bounds is a tuple defined as (xMin, yMin, xMax, yMax)
        bounds = (
            min(orig_bounds[0], orig_bounds[2]),
            min(extents.descender, extents.ascender),
            max(orig_bounds[0], orig_bounds[2]),
            max(extents.descender, extents.ascender),
        )
        bounds = scaleRect(bounds, scaleFactor, scaleFactor)
        bounds = insetRect(bounds, -self.margin, -self.margin)
        bounds = intRect(bounds)
        surfaceClass = getSurfaceClass("skia", ".png")

        surface = surfaceClass()
        # return empty canvas if either width or height == 0. Not doing so
        # causes Skia to raise a null pointer error
        if orig_bounds[0] == orig_bounds[2] or \
            orig_bounds[1] == orig_bounds[3]:
            return Image.new("RGBA", (0,0))
        with surface.canvas(bounds) as canvas:
            canvas.scale(scaleFactor)
            for glyph in glyphLine:
                with canvas.savedState():
                    canvas.translate(glyph.xOffset, glyph.yOffset)
                    font.drawGlyph(glyph.name, canvas)
                canvas.translate(glyph.xAdvance, glyph.yAdvance)
        return Image.fromarray(surface._image.toarray())

    # This code was an attempt to render black-and-white fonts
    # quickly using Freetype and numpy. It was very fast and very
    # clever, but there were various things we couldn't get working
    # (in particular, vertical placement of glyphs with offsets)
    # so we've parked it for now.

    # def render_text_ft(self, text: str):
    #     ft_face = self.font.ftFont
    #     ft_face.set_char_size(self.font_size * 64)
    #     buf = self.shape(text)
    #     pen = ft.FT_Vector(0, 0)
    #     xmin, xmax = 0, 0
    #     ymin, ymax = 0, 0

    #     if not buf.glyph_infos or not buf.glyph_positions:
    #         logger.error("Shaping failed for string '%s'", textString)
    #         return np.array([])

    #     for glyph, pos in zip(buf.glyph_infos, buf.glyph_positions):
    #         bitmap = get_cached_bitmap(ft_face, glyph.codepoint, self.cache)
    #         width = bitmap.width
    #         rows = bitmap.rows
    #         x0 = (pen.x >> 6) + bitmap.left + (pos.x_offset >> 6)
    #         x1 = x0 + width
    #         y0 = (pen.y >> 6) - (bitmap.rows - bitmap.top) + (pos.y_offset >> 6)
    #         y1 = y0 + rows
    #         xmin, xmax = min(xmin, x0), max(xmax, x1)
    #         ymin, ymax = min(ymin, y0), max(ymax, y1)
    #         pen.x += pos.x_advance
    #         pen.y += pos.y_advance

    #     L = np.zeros((ymax - ymin, xmax - xmin), dtype=np.ubyte)
    #     pen.x, pen.y = 0, 0
    #     for glyph, pos in zip(buf.glyph_infos, buf.glyph_positions):
    #         bitmap = get_cached_bitmap(ft_face, glyph.codepoint, self.cache)
    #         x = (pen.x >> 6) - xmin + bitmap.left + (pos.x_offset >> 6)
    #         y = (pen.y >> 6) - ymin - (bitmap.rows - bitmap.top) + (pos.y_offset >> 6)
    #         data = []
    #         for j in range(bitmap.rows):
    #             data.extend(bitmap.buffer[j * bitmap.pitch : j * bitmap.pitch + bitmap.width])
    #         if len(data):
    #             Z = np.array(data, dtype=np.ubyte).reshape(bitmap.rows, bitmap.width)
    #             L[y : y + bitmap.rows, x : x + bitmap.width] |= Z
    #         pen.x += pos.x_advance
    #         pen.y += pos.y_advance
    #     return Image.fromarray(L)

@dataclass
class Bitmap:
    buffer: any
    width: int
    rows: int
    top: int
    left: int
    pitch: int

def get_cached_bitmap(ft_face, codepoint, cache):
    if codepoint in cache:
        return cache[codepoint]
    flags = ft.FT_LOAD_NO_HINTING | ft.FT_LOAD_RENDER
    ft_face.load_glyph(codepoint, flags)
    bitmap = ft_face.glyph.bitmap
    cache[codepoint] = Bitmap(
        buffer=bitmap.buffer,
        width = bitmap.width,
        rows = bitmap.rows,
        top = ft_face.glyph.bitmap_top,
        left = ft_face.glyph.bitmap_left,
        pitch = ft_face.glyph.bitmap.pitch,
    )
    return cache[codepoint]


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
            font_size=FONT_SIZE,
            margin=0,
            features=self.features,
            script=self.script,
            lang=self.lang,
            variations=getattr(self.font_a, "variations", None)
        )
        self.renderer_b = Renderer(
            self.font_b,
            font_size=FONT_SIZE,
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
        img_a = self.renderer_a.render(string)
        img_b = self.renderer_b.render(string)
        width = min([img_a.width, img_b.width])
        height = min([img_a.height, img_b.height])
        img_a = np.asarray(img_a)[0:height, 0:width, :]
        img_b = np.asarray(img_b)[0:height, 0:width, :]

        diff_map = np.abs(img_a-img_b)
        if np.size(diff_map) == 0:
            return 0, []
        pc = np.sum(diff_map) / np.size(diff_map)
        return pc, diff_map


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Draw some text")
    parser.add_argument("font", metavar="TTF")
    parser.add_argument("string", metavar="TEXT")
    parser.add_argument("--out", "-o", metavar="PNG", default="out.png")
    parser.add_argument("--lang", metavar="LANGUAGE")
    parser.add_argument("--script", metavar="SCRIPT")
    parser.add_argument("--features", metavar="FEATURES")
    parser.add_argument("--variations", metavar="VARIATIONS")
    parser.add_argument("-pt", help="point size", default=250, type=int)
    # TODO add variations
    args = parser.parse_args()

    font = DFont(args.font)
    features = None
    if args.features:
        features = {}
        for f in args.features.split(","):
            if f[0] == "-":
                features[f[1:]] = False
            elif f[0] == "+":
                features[f[1:]] = True
            else:
                features[f] = True

    variations = None
    if args.variations:
        variations = {}
        for f in args.variations.split(","):
            axis, loc = f.split("=")
            variations[axis] = float(loc)

    img = Renderer(
        font,
        features=features,
        lang=args.lang,
        script=args.script,
        font_size=args.pt,
        variations=variations
    ).render(args.string)
    img.save(args.out)
