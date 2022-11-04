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
from diffenator.font import DFont
import numpy as np
import freetype as ft


logger = logging.getLogger(__name__)


def render_text(
    font: DFont,
    textString: str,
    *,
    fontSize: int = 250,
    margin: int = 20,
    features: dict[str, bool] = None,
    variations: dict[str, float] = None,
    lang: str = None,
    script: str = None,
):
    if font.is_color():
        return render_text_cairo(
            font,
            textString,
            fontSize=fontSize,
            margin=margin,
            features=None,
            variations=None,
            lang=None,
            script=None,
        )
    return render_text_ft(
        font,
        textString,
        fontSize=fontSize,
        margin=margin,
        features=None,
        variations=None,
        lang=None,
        script=None,
    )


def render_text_cairo(
    font: DFont,
    textString: str,
    *,
    fontSize: int = 250,
    margin: int = 20,
    features: dict[str, bool] = None,
    variations: dict[str, float] = None,
    lang: str = None,
    script: str = None,
):
    font = font.blackFont
    glyphNames = font.glyphNames

    scaleFactor = fontSize / font.unitsPerEm

    buf = hb.Buffer()
    buf.add_str(textString)
    buf.guess_segment_properties()

    if script:
        buf.script = script
    if lang:
        buf.language = lang
    if variations:
        font.setLocation(variations)

    hb.shape(font.hbFont, buf, features)

    infos = buf.glyph_infos
    positions = buf.glyph_positions
    glyphLine = buildGlyphLine(infos, positions, glyphNames)
    bounds = calcGlyphLineBounds(glyphLine, font)
    bounds = scaleRect(bounds, scaleFactor, scaleFactor)
    bounds = insetRect(bounds, -margin, -margin)
    bounds = intRect(bounds)
    surfaceClass = getSurfaceClass("skia", ".png")

    surface = surfaceClass()
    with surface.canvas(bounds) as canvas:
        canvas.scale(scaleFactor)
        for glyph in glyphLine:
            with canvas.savedState():
                canvas.translate(glyph.xOffset, glyph.yOffset)
                font.drawGlyph(glyph.name, canvas)
            canvas.translate(glyph.xAdvance, glyph.yAdvance)
    return Image.fromarray(surface._image.toarray())


def render_text_ft(
    font: DFont,
    textString: str,
    *,
    fontSize: int = 250,
    margin: int = 20,
    features: dict[str, bool] = None,
    variations: dict[str, float] = None,
    lang: str = None,
    script: str = None,
):
    # TODO image is currently flipped vertically.
    ft_face = font.ftFont
    ft_face.set_char_size(fontSize * 64)
    flags = ft.FT_LOAD_NO_HINTING | ft.FT_LOAD_RENDER
    pen = ft.FT_Vector(0, 0)
    xmin, xmax = 0, 0
    ymin, ymax = 0, 0
    hb_font = font.hbFont
    hb_font.scale = (fontSize * 64, fontSize * 64)
    hb.ot_font_set_funcs(hb_font)
    buf = hb.Buffer()
    buf.add_str(textString)
    buf.guess_segment_properties()
    if script:
        buf.script = str(script)
    if lang:
        buf.language = str(lang)
    hb.shape(hb_font, buf, features)
    if not buf.glyph_infos or not buf.glyph_positions:
        logger.error("Shaping failed for string '%s'", textString)
        return np.array([])

    for glyph, pos in zip(buf.glyph_infos, buf.glyph_positions):
        ft_face.load_glyph(glyph.codepoint, flags)
        bitmap = ft_face.glyph.bitmap
        width = bitmap.width
        rows = bitmap.rows
        top = ft_face.glyph.bitmap_top
        left = ft_face.glyph.bitmap_left
        x0 = (pen.x >> 6) + left + (pos.x_offset >> 6)
        x1 = x0 + width
        y0 = (pen.y >> 6) - (rows - top) + (pos.y_offset >> 6)
        y1 = y0 + rows
        xmin, xmax = min(xmin, x0), max(xmax, x1)
        ymin, ymax = min(ymin, y0), max(ymax, y1)
        pen.x += pos.x_advance
        pen.y += pos.y_advance

    L = np.zeros((ymax - ymin, xmax - xmin), dtype=np.ubyte)
    previous = 0
    pen.x, pen.y = 0, 0
    for glyph, pos in zip(buf.glyph_infos, buf.glyph_positions):
        ft_face.load_glyph(glyph.codepoint, flags)
        pitch = ft_face.glyph.bitmap.pitch
        width = bitmap.width
        rows = bitmap.rows
        top = ft_face.glyph.bitmap_top
        left = ft_face.glyph.bitmap_left
        x = (pen.x >> 6) - xmin + left + (pos.x_offset >> 6)
        y = (pen.y >> 6) - ymin - (rows - top) + (pos.y_offset >> 6)
        data = []
        for j in range(rows):
            data.extend(bitmap.buffer[j * pitch : j * pitch + width])
        if len(data):
            Z = np.array(data, dtype=np.ubyte).reshape(rows, width)
            L[y : y + rows, x : x + width] |= Z[::-1, ::1]
        pen.x += pos.x_advance
        pen.y += pos.y_advance
    return Image.fromarray(L)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Draw some text")
    parser.add_argument("font", metavar="TTF")
    parser.add_argument("string", metavar="TEXT")
    parser.add_argument("--out", "-o", metavar="PNG", default="out.png")
    parser.add_argument("--lang", metavar="LANGUAGE")
    parser.add_argument("--script", metavar="SCRIPT")
    parser.add_argument("--features", metavar="FEATURES")
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

    img = render_text(
        font,
        args.string,
        features=features,
        lang=args.lang,
        script=args.script,
        fontSize=args.pt,
    )
    img.save(args.out)
