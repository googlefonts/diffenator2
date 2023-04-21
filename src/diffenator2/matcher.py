"""
Match font styles or match vf coordinates


VF coordinate matcher:

>>> matcher = FontMatcher(font_a, font_b)
>>> matcher.masters()

[
    (wght=400,),
    (wght=900,),
]

>>> matcher.cross_product()

[
    (wght=400,), # these should be style objects
    (wght=700,),
    (wght=900,),
]

>>> matcher.instances() # should be default

>>> style.name 

Regular # static
wght-400 # vf

>>> style.axes

{
    wght: 400,
    wdth: 75,
}


>>> style.position

(old, new)

>>> 



matcher = FontMatcher(old_fonts, new_fonts)
old, new = matcher.coordinates({wght: 400})

(
    (old_instance("wght-400", {wght:400})),
    (new_instance("wght-400", {wght: 400}),
)

old = old[0]
new = new[0]

old.


## Diffenator

old_font = ...
new_font = ...
coords = {wght=400}


matcher = FontMatcher([old_font], [new_font])
matcher.cross_product()

for old_style, new_style in matcher.styles:
    old_style.set_font_variations()
    new_style.set_font_variations()

    diff = DiffFonts(old_style.font, new_style.font)
    diff.all()
    diff.to_html("out.html")

    
## Diffbrowsers

old_fonts = ...
new_fonts = ...

matcher = FontMatcher(old_fonts, new_fonts)
matcher.masters()


diff_rendering(matcher) or proof_rendering(matcher)

"""
from diffenator2.font import get_font_styles, Style
from fontTools.ttLib.scaleUpem import scale_upem


class FontMatcher:

    def __init__(self, old_fonts, new_fonts):
        self.old_fonts = old_fonts
        self.new_fonts = new_fonts
        self.old_styles = []
        self.new_styles = []
    
    def _match_styles(self, type_, filter_styles=None):
        old_styles = {s.name: s for s in get_font_styles(self.old_fonts, type_, filter_styles)}
        new_styles = {s.name: s for s in get_font_styles(self.new_fonts, type_, filter_styles)}

        matching = set(old_styles.keys()) & set(new_styles.keys())
        self.old_styles = [old_styles[s] for s in matching]
        self.new_styles = [new_styles[s] for s in matching]

    def instances(self, filter_styles=None):
        self._match_styles("instances", filter_styles)

    def cross_product(self, filter_styles=None):
        old_styles = []
        new_styles = []
        styles = get_font_styles(self.new_fonts, "cross_product", filter_styles)
        # TODO work out best matching fonts. Current implementation only works on a single font
        old_font = self.old_fonts[0]
        for style in styles:
            old_style = old_font.closest_style(style.coords)
            if old_style:
                old_styles.append(old_style)
                new_styles.append(Style(style.font, old_style.name, old_style.coords))
        self.old_styles = old_styles
        self.new_styles = new_styles

    def masters(self, filter_styles):
        pass
    
    def coordinates(self, coords=None):
        # TODO add validation
        from diffenator2.font import Style
        from diffenator2.utils import dict_coords_to_string
        for font in self.old_fonts:
            style_name = dict_coords_to_string(coords).replace(",", "_").replace("=", "-").replace(".", "-")
            self.old_styles.append(Style(font, style_name, coords))
        
        for font in self.new_fonts:
            style_name = dict_coords_to_string(coords).replace(",", "_").replace("=", "-").replace(".", "-")
            self.new_styles.append(Style(font, style_name, coords))
    
    def upms(self):
        assert self.old_styles + self.new_styles, "match styles first!"
        seen = set()
        for old_style, new_style in zip(self.old_styles, self.new_styles):
            if old_style in seen:
                continue
            scale_upem(old_style.font.ttFont, new_style.font.ttFont["head"].unitsPerEm)
            seen.add(old_style)
