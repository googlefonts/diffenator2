"""
Revisitng rendering html pages

What's wrong with what we've got. Feels overengineered!

What do we need to do:

- Proof a font/fonts
- Diff 1 set of font/fonts against another
- Diffenate 1 set of font/fonts against another (feels like the above)

Let's start by making them as their own simple functions
"""
from dataclasses import dataclass, field
from jinja2 import Template, Environment, FileSystemLoader
from fontTools.ttLib import TTFont
import os
from diffenator.shape import Renderable


def proof_rendering(ttFonts, template_dir):
    font_faces = [CSSFontFace(f) for f in ttFonts]
    font_styles = [CSSFontStyle(f) for f in ttFonts]
    env = Environment(
        loader=FileSystemLoader(template_dir),
    )
    template = env.get_template("waterfall.html")
    doc = template.render(
        font_faces=font_faces,
        font_styles=font_styles,
    )
    print(doc)


def diff_rendering(ttFonts_old, ttFonts_new, template_dir):
    font_faces_old = [CSSFontFace(f, "old") for f in ttFonts_old]
    font_styles_old = [CSSFontStyle(f, "old") for f in ttFonts_old]
    
    font_faces_new = [CSSFontFace(f, "new") for f in ttFonts_new]
    font_styles_new = [CSSFontStyle(f, "new") for f in ttFonts_new]

    font_styles_old, font_styles_new = _match_styles(
        font_styles_old, font_styles_new
    )
    with open(template) as doc:
        temp = Template(doc.read())
        print(temp.render(
            font_faces_old=font_faces_old,
            font_styles_old=font_styles_old,
            font_faces_new=font_faces_new,
            font_styles_new=font_styles_new,
        ))

from diffenator.shape import Renderable

@dataclass
class CSSFontFace(Renderable):
    ttfont: TTFont
    suffix: str = ""
    filename: str = field(init=False)
    familyname: str = field(init=False)
    
    def __post_init__(self):
        self.filename = os.path.basename(self.ttfont.reader.file.name)
        self.familyname = self.ttfont['name'].getBestFamilyName()


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


def _match_styles(styles_old: list[CSSFontStyle], styles_new: list[CSSFontStyle]):
    old = {s.stylename: s for s in styles_old}
    new = {s.stylename: s for s in styles_new}
    shared = set(old) & set(new)
    if not shared:
        raise ValueError("No matching fonts found")
    return [old[s] for s in shared], [new[s] for s in shared]


if __name__ == "__main__":
    import os
    fonts = [TTFont(os.environ["mavenvf"]), TTFont("/Users/marcfoley/Type/fonts/ofl/exo/Exo[wght].ttf")]
    proof_rendering(fonts, template_dir="templates")