"""
"""
from dataclasses import dataclass, field
from jinja2 import Environment, FileSystemLoader
from fontTools.ttLib import TTFont
import os
import shutil
from diffenator.shape import Renderable


@dataclass
class CSSFontFace(Renderable):
    ttfont: TTFont
    suffix: str = ""
    filename: str = field(init=False)
    familyname: str = field(init=False)

    def __post_init__(self):
        self.filename = os.path.basename(self.ttfont.reader.file.name)
        self.familyname = self.ttfont["name"].getBestFamilyName()


@dataclass
class CSSFontStyle(Renderable):
    ttfont: TTFont
    suffix: str = ""
    font_weight: int = field(init=False)
    familyname: str = field(init=False)
    stylename: str = field(init=False)

    def __post_init__(self):
        self.font_weight = self.ttfont["OS/2"].usWeightClass
        self.familyname = self.ttfont["name"].getBestFamilyName()
        self.stylename = self.ttfont["name"].getBestSubFamilyName()


def proof_rendering(ttFonts, template, dst="out"):
    font_faces = [CSSFontFace(f) for f in ttFonts]
    font_styles = [CSSFontStyle(f) for f in ttFonts]
    _package(template, dst, font_faces=font_faces, font_styles=font_styles)


def diff_rendering(ttFonts_old, ttFonts_new, template_fp, dst="out"):
    font_faces_old = [CSSFontFace(f, "old") for f in ttFonts_old]
    font_styles_old = [CSSFontStyle(f, "old") for f in ttFonts_old]

    font_faces_new = [CSSFontFace(f, "new") for f in ttFonts_new]
    font_styles_new = [CSSFontStyle(f, "new") for f in ttFonts_new]

    font_styles_old, font_styles_new = _match_styles(font_styles_old, font_styles_new)
    _package(
        template_fp,
        dst,
        font_faces_old=font_faces_old,
        font_styles_old=font_styles_old,
        font_faces_new=font_faces_new,
        font_styles_new=font_styles_new,
    )


def _package(template_fp, dst, **kwargs):
    if not os.path.exists(dst):
        os.mkdir(dst)

    # write doc
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(template_fp)),
    )
    template = env.get_template(os.path.basename(template_fp))
    doc = template.render(**kwargs)
    dst_doc = os.path.join(dst, os.path.basename(template_fp))
    with open(dst_doc, "w") as out_file:
        out_file.write(doc)

    # copy fonts
    if "font_faces" in kwargs:
        for font_face in kwargs["font_faces"]:
            out_fp = os.path.join(dst, font_face.filename)
            shutil.copy(font_face.ttfont.reader.file.name, out_fp)
    # TODO fonts before and fonts after


def _match_styles(styles_old: list[CSSFontStyle], styles_new: list[CSSFontStyle]):
    old = {s.stylename: s for s in styles_old}
    new = {s.stylename: s for s in styles_new}
    shared = set(old) & set(new)
    if not shared:
        raise ValueError("No matching fonts found")
    return [old[s] for s in shared], [new[s] for s in shared]


if __name__ == "__main__":
    import os

    fonts = [
        TTFont(os.environ["mavenvf"]),
        TTFont("/Users/marcfoley/Type/fonts/ofl/exo/Exo[wght].ttf"),
    ]
    proof_rendering(fonts, template="templates/waterfall.html", dst="out")
