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

class FontMatcher:

    def __init__(self, old_fonts, new_fonts):
        self.old_fonts = old_fonts
        self.new_fonts = new_fonts
        self.old_styles = []
        self.new_styles = []
    
    def instances(self):
        def get_styles(fonts):
            results = {}
            for font in fonts:
                for style in font.instances():
                    results[style.name] = style
            return results

        old_styles = get_styles(self.old_fonts)
        new_styles = get_styles(self.new_fonts)

        matching = set(old_styles.keys()) & set(new_styles.keys())
        self.old_styles = [old_styles[s] for s in matching]
        self.new_styles = [new_styles[s] for s in matching]

    def cross_product(self):
        pass

    def masters(self):
        pass
    
    def coordinates(self, coords=None):
        pass
