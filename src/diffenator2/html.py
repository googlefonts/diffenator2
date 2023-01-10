"""
"""
from __future__ import annotations
from jinja2 import Environment, FileSystemLoader
from fontTools.ttLib import TTFont
import os
import shutil
from diffenator2.template_elements import CSSFontStyle, CSSFontFace
from diffenator2.utils import font_sample_text
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


def diffenator_font_face(dfont, suffix=""):
    face = CSSFontFace(dfont, suffix)
    face.cssfamilyname = f"{suffix} font"
    return face


def diffenator_font_style(dfont, suffix=""):
    ttfont = dfont.ttFont
    if dfont.is_variable() and hasattr(dfont, "variations"):
        style_name = ttfont["name"].getBestSubFamilyName()
        coords = dfont.variations
    else:
        style_name = ttfont["name"].getBestSubFamilyName()
        coords = {"wght": ttfont["OS/2"].usWeightClass}
    return CSSFontStyle(
        "font",
        "style",
        coords,
        suffix,
    )


def proof_rendering(ttFonts, templates, dst="out", filter_styles=None, pt_size=20):
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
        pt_size=pt_size,
    )


def diff_rendering(ttFonts_old, ttFonts_new, templates, dst="out", filter_styles=None, pt_size=20):
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
        pt_size=pt_size,
    )


def diffenator_report(diff, template, dst="out"):
    font_faces_old = [diffenator_font_face(diff.old_font.ttFont, "old")]
    font_faces_new = [diffenator_font_face(diff.new_font.ttFont, "new")]

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
        os.makedirs(dst)

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
    old = {s.stylename: s for s in styles_old}
    new = {s.stylename: s for s in styles_new}
    shared = set(old) & set(new)
    if not shared:
        raise ValueError("No matching fonts found")
    return [s for s in styles_old if s.stylename in shared], [
        s for s in styles_new if s.stylename in shared
    ]
