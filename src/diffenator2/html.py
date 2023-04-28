"""
"""
from __future__ import annotations
from jinja2 import Environment, FileSystemLoader
from fontTools.ttLib import TTFont
import os
import shutil
from diffenator2.template_elements import CSSFontStyle, CSSFontFace
from diffenator2.utils import font_sample_text
from glyphsets import GFTestData
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


def proof_rendering(styles, templates, dst="out", filter_styles=None, pt_size=20):
    ttFont = styles[0].font.ttFont
    font_faces = set(style.font.css_font_face for style in styles)
    font_styles = [style.css_font_style for style in styles]
    sample_text = " ".join(font_sample_text(ttFont))
    test_strings = GFTestData.test_strings_in_font(ttFont)
    glyphs = [chr(c) for c in ttFont.getBestCmap()]
    _package(
        templates,
        dst,
        font_faces=font_faces,
        font_styles=font_styles,
        sample_text=sample_text,
        glyphs=glyphs,
        test_strings=test_strings,
        pt_size=pt_size,
    )


def diff_rendering(matcher, templates, dst="out", filter_styles=None, pt_size=20):
    ttFont = matcher.old_styles[0].font.ttFont
    font_faces_old = set(style.font.css_font_face for style in matcher.old_styles)
    font_styles_old = [style.css_font_style for style in matcher.old_styles]
    
    font_faces_new = set(style.font.css_font_face for style in matcher.new_styles)
    font_styles_new = [style.css_font_style for style in matcher.new_styles]

    sample_text = " ".join(font_sample_text(ttFont))
    test_strings = GFTestData.test_strings_in_font(ttFont)
    glyphs = [chr(c) for c in ttFont.getBestCmap()]
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
        test_strings=test_strings,
        pt_size=pt_size,
    )


def diffenator_report(diff, template, dst="out"):
    font_faces_old = [diff.old_font.css_font_face]
    font_faces_old[0].cssfamilyname = "old font"
    font_faces_new = [diff.new_font.css_font_face]
    font_faces_new[0].cssfamilyname = "new font"

    font_styles_old = [diff.old_style.css_font_style]
    font_styles_old[0].cssfamilyname = "old font"
    font_styles_new = [diff.new_style.css_font_style]
    font_styles_new[0].cssfamilyname = "new font"
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
