"""
"""
from __future__ import annotations
from dataclasses import dataclass, field
from jinja2 import Environment, FileSystemLoader
from fontTools.ttLib import TTFont
import os
import shutil
from diffenator.shape import Renderable
from diffenator.utils import font_sample_text
import re


WIDTH_CLASS_TO_CSS = {
    1: "50",
    2: "62.5",
    3: "75",
    4: "87.5",
    5: "100",
    6: "112.5",
    7: "125",
    8: "150",
    9: "200",
}


@dataclass
class CSSFontFace(Renderable):
    ttfont: TTFont
    suffix: str = ""
    filename: str = field(init=False)
    familyname: str = field(init=False)
    classname: str = field(init=False)

    def __post_init__(self):
        ttf_filename = os.path.basename(self.ttfont.reader.file.name)
        if self.suffix:
            self.filename = f"{self.suffix}-{ttf_filename}"
        else:
            self.filename = ttf_filename
        self.cssfamilyname = _family_name(self.ttfont, self.suffix)
        self.stylename = self.ttfont["name"].getBestSubFamilyName()
        self.classname = self.cssfamilyname.replace(" ", "-")
        self.font_style = "normal" if "Italic" not in self.stylename else "italic"

        if "fvar" in self.ttfont:
            fvar = self.ttfont["fvar"]
            axes = {a.axisTag: a for a in fvar.axes}
            if "wght" in axes:
                min_weight = int(axes["wght"].minValue)
                max_weight = int(axes["wght"].maxValue)
                self.font_weight = f"{min_weight} {max_weight}"
            if "wdth" in axes:
                min_width = int(axes["wdth"].minValue)
                max_width = int(axes["wdth"].maxValue)
                self.font_stretch = f"{min_width}% {max_width}%"
            if "ital" in axes:
                pass
            if "slnt" in axes:
                min_angle = int(axes["slnt"].minValue)
                max_angle = int(axes["slnt"].maxValue)
                self.font_style = f"oblique {min_angle}deg {max_angle}deg"


def _family_name(ttFont, suffix=""):
    familyname = ttFont["name"].getBestFamilyName()
    if suffix:
        return f"{suffix} {familyname}"
    else:
        return familyname


@dataclass
class CSSFontStyle(Renderable):
    familyname: str
    stylename: str
    coords: dict
    suffix: str = ""

    def __post_init__(self):
        if self.suffix:
            self.cssfamilyname = f"{self.suffix} {self.familyname}"
        else:
            self.cssfamilyname = self.familyname
        self.full_name = f"{self.familyname} {self.stylename}"
        if self.suffix:
            self.class_name = (
                f"{self.suffix} {self.familyname} {self.stylename}".replace(" ", "-")
            )
        else:
            self.class_name = f"{self.familyname} {self.stylename}".replace(" ", "-")


def get_font_styles(ttfonts, suffix="", filters=None):
    res = []
    for ttfont in ttfonts:
        family_name = ttfont["name"].getBestFamilyName()
        style_name = ttfont["name"].getBestSubFamilyName()
        if "fvar" in ttfont:
            fvar = ttfont["fvar"]
            for inst in fvar.instances:
                name_id = inst.subfamilyNameID
                style_name = ttfont["name"].getName(name_id, 3, 1, 0x409).toUnicode()
                coords = inst.coordinates
                if filters and not re.match(filters, style_name):
                    continue
                res.append(CSSFontStyle(family_name, style_name, coords, suffix))
        else:
            if filters and not any(re.match(f, style_name) for f in filters):
                continue 
            res.append(static_font_style(ttfont, suffix))
    return res


def static_font_style(ttfont, suffix=""):
    family_name = ttfont["name"].getBestFamilyName()
    style_name = ttfont["name"].getBestSubFamilyName()
    return CSSFontStyle(
        family_name,
        style_name,
        {
            "wght": ttfont["OS/2"].usWeightClass,
            "wdth": WIDTH_CLASS_TO_CSS[ttfont["OS/2"].usWidthClass],
        },
        suffix,
    )


def diffenator_font_style(dfont, suffix=""):
    ttfont = dfont.ttFont
    family_name = ttfont["name"].getBestFamilyName()
    if dfont.is_variable() and hasattr(dfont, "variations"):
        name_id = next(
            (
                i.subfamilyNameID
                for i in ttfont["fvar"].instances
                if i.coordinates == dfont.variations
            ),
            None,
        )
        style_name = ttfont["name"].getName(name_id, 3, 1, 0x409).toUnicode()
        coords = dfont.variations
    else:
        style_name = ttfont["name"].getBestSubFamilyName()
        coords = {"wght": ttfont["OS/2"].usWeightClass}
    return CSSFontStyle(
        family_name,
        style_name,
        coords,
        suffix,
    )


def proof_rendering(ttFonts, templates, dst="out", filter_styles=None):
    font_faces = [CSSFontFace(f) for f in ttFonts]
    font_styles = get_font_styles(ttFonts, filters=filter_styles)
    sample_text = " ".join(font_sample_text(ttFonts[0]))
    glyphs = [chr(c) for c in ttFonts[0].getBestCmap()]
    _package(
        templates,
        dst,
        font_faces=font_faces,
        font_styles=font_styles,
        sample_text=sample_text,
        glyphs=glyphs,
        pt_size=20,
    )


def diff_rendering(ttFonts_old, ttFonts_new, templates, dst="out", filter_styles=None):
    font_faces_old = [CSSFontFace(f, "old") for f in ttFonts_old]
    font_styles_old = get_font_styles(ttFonts_old, "old", filters=filter_styles)

    font_faces_new = [CSSFontFace(f, "new") for f in ttFonts_new]
    font_styles_new = get_font_styles(ttFonts_new, "new", filters=filter_styles)

    font_styles_old, font_styles_new = _match_styles(font_styles_old, font_styles_new)

    sample_text = " ".join(font_sample_text(ttFonts_old[0]))
    glyphs = [chr(c) for c in ttFonts_old[0].getBestCmap()]
    _package(
        templates,
        dst,
        font_faces_old=font_faces_old,
        font_styles_old=font_styles_old,
        font_faces_new=font_faces_new,
        font_styles_new=font_styles_new,
        include_ui=True,
        sample_text=sample_text,
        glyphs=glyphs,
        pt_size=20,
    )


def diffenator_report(diff, template, dst="out"):
    font_faces_old = [CSSFontFace(diff.old_font.ttFont, "old")]
    font_faces_new = [CSSFontFace(diff.new_font.ttFont, "new")]

    font_styles_old = [diffenator_font_style(diff.old_font, "old")]
    font_styles_new = [diffenator_font_style(diff.new_font, "new")]
    _package(
        [template],
        dst,
        diff=diff,
        font_faces_old=font_faces_old,
        font_faces_new=font_faces_new,
        font_styles_old=font_styles_old,
        font_styles_new=font_styles_new,
        include_ui=True,
        pt_size=32,
    )


def _package(templates, dst, **kwargs):
    if not os.path.exists(dst):
        os.mkdir(dst)

    # write docs
    for template_fp in templates:
        env = Environment(
            loader=FileSystemLoader(os.path.dirname(template_fp)),
        )
        template = env.get_template(os.path.basename(template_fp))
        doc = template.render(**kwargs)
        dst_doc = os.path.join(dst, os.path.basename(template_fp))
        with open(dst_doc, "w", encoding="utf8") as out_file:
            out_file.write(doc)

    # copy fonts
    # make this more general purpose for ttfont objects
    for k in ("font_faces", "font_faces_old", "font_faces_new"):
        if k in kwargs:
            for font in kwargs[k]:
                out_fp = os.path.join(dst, font.filename)
                shutil.copy(font.ttfont.reader.file.name, out_fp)


def _match_styles(styles_old: list[CSSFontStyle], styles_new: list[CSSFontStyle]):
    old = {s.full_name: s for s in styles_old}
    new = {s.full_name: s for s in styles_new}
    shared = set(old) & set(new)
    if not shared:
        raise ValueError("No matching fonts found")
    return [s for s in styles_old if s.full_name in shared], [
        s for s in styles_new if s.full_name in shared
    ]
