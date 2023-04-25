"""
Match font styles or match vf coordinates
"""
from diffenator2.font import get_font_styles, Style
from fontTools.ttLib.scaleUpem import scale_upem
import re


class FontMatcher:

    def __init__(self, old_fonts, new_fonts):
        self.old_fonts = old_fonts
        self.new_fonts = new_fonts
        self.old_styles = []
        self.new_styles = []
    
    def _match_fonts(self):
        old_fonts = []
        new_fonts = []
        for new_font in self.new_fonts:
            new_names = self._get_names(new_font)
            best_font = None
            match_count = -float("inf")
            for old_font in self.old_fonts:
                if old_font == new_font:
                    continue
                old_names = self._get_names(old_font)
                matched_names = old_names & new_names
                if len(matched_names) > match_count:
                    match_count = len(matched_names)
                    best_font = old_font
            old_fonts.append(best_font)
            new_fonts.append(new_font)
        self.old_fonts = old_fonts
        self.new_fonts = new_fonts

    def _get_names(self, font):
        results = set()
        name = font.ttFont["name"]
        fvar = font.ttFont["fvar"]
        # TODO add STAT
        results.add(name.getBestSubFamilyName())
        for inst in fvar.instances:
            results.add(name.getName(inst.subfamilyNameID, 3, 1, 0x409).toUnicode())
        return results

    def _match_styles(self, type_, filter_styles=None):
        old_styles = {s.name: s for s in get_font_styles(self.old_fonts, type_, filter_styles)}
        new_styles = {s.name: s for s in get_font_styles(self.new_fonts, type_, filter_styles)}

        matching = set(old_styles.keys()) & set(new_styles.keys())
        self.old_styles = [old_styles[s] for s in matching]
        self.new_styles = [new_styles[s] for s in matching]

    def instances(self, filter_styles=None):
        self._match_styles("instances", filter_styles)

    def cross_product(self, filter_styles=None):
        self._match_fonts()
        styles = get_font_styles(self.new_fonts, "cross_product", filter_styles)
        self._closest_match(styles, filter_styles)

    def masters(self, filter_styles=None):
        self._match_fonts()
        styles = get_font_styles(self.new_fonts, "masters")
        self._closest_match(styles, filter_styles)

    def _closest_match(self, styles, filter_styles=None):
        # TODO work out best matching fonts. Current implementation only works on a single font
        assert all(f.is_variable() for f in self.old_fonts+self.new_fonts), "All fonts must be variable fonts"
        old_font = self.old_fonts[0]
        old_styles = []
        new_styles = []
        seen = set()
        for style in styles:
            old_style = old_font.closest_style(style.coords)
            if old_style and old_style.name not in seen:
                seen.add(old_style.name)
                old_styles.append(old_style)
                new_styles.append(Style(style.font, old_style.coords))

        if filter_styles:
            old_styles = [s for s in old_styles if re.match(filter_styles, s.name)]
            new_styles = [s for s in new_styles if re.match(filter_styles, s.name)]

        self.old_styles = sorted([s for s in old_styles], key=lambda k: [v for v in k.coords.values()])
        self.new_styles = sorted([s for s in new_styles], key=lambda k: [v for v in k.coords.values()])

    def coordinates(self, coords=None):
        # TODO add validation
        for font in self.old_fonts:
            self.old_styles.append(Style(font, coords))
        
        for font in self.new_fonts:
            self.new_styles.append(Style(font, coords))
    
    def upms(self):
        assert self.old_styles + self.new_styles, "match styles first!"
        seen = set()
        for old_style, new_style in zip(self.old_styles, self.new_styles):
            if old_style in seen:
                continue
            scale_upem(old_style.font.ttFont, new_style.font.ttFont["head"].unitsPerEm)
            seen.add(old_style)
