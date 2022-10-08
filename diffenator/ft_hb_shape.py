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


logger = logging.getLogger(__name__)


def render_text(
    font,
    textString,
    *,
    fontSize=250,
    margin=20,
    features=None,
    variations=None,
    backendName=None,
    lang=None,
    script=None,
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Draw some text")
    parser.add_argument("font", metavar="TTF")
    parser.add_argument("string", metavar="TEXT")
    parser.add_argument("--out", "-o", metavar="PNG", default="out.png")
    parser.add_argument("--lang", metavar="LANGUAGE")
    parser.add_argument("--script", metavar="SCRIPT")
    parser.add_argument("--features", metavar="FEATURES")
    parser.add_argument("-pt", help="point size", default=250, type=int)
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
