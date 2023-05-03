"""
Match font styles or match vf coordinates
"""
from diffenator2.font import get_font_styles, Style, DFont
from fontTools.ttLib.scaleUpem import scale_upem
from typing import List
import re


class FontMatcher:

    def __init__(self, old_fonts: List[DFont], new_fonts: List[DFont]):
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

    def _get_names(self, font: DFont):
        results = set()
        name = font.ttFont["name"]
        fvar = font.ttFont["fvar"]
        # TODO add STAT
        results.add(name.getBestSubFamilyName())
        for inst in fvar.instances:
            results.add(name.getName(inst.subfamilyNameID, 3, 1, 0x409).toUnicode())
        return results
    
    def diffenator(self, coords=None):
        assert len(self.old_fonts) == 1 and len(self.new_fonts) == 1, "Multiple fonts found. Diffenator can only do a 1 on 1 comparison"
        old_font = self.old_fonts[0]
        new_font = self.new_fonts[0]
        if old_font.is_variable() and new_font.is_variable():
            if not coords:
                coords = {a.axisTag: a.defaultValue for a in new_font.ttFont["fvar"].axes}
            self.old_styles.append(Style(old_font, coords, ""))
            self.new_styles.append(Style(new_font, coords, ""))
            old_font.set_variations(coords)
            new_font.set_variations(coords)
        elif old_font.is_variable() and not new_font.is_variable():
            self.instances()
            old_font.set_variations_from_static_font(new_font)
        elif new_font.is_variable() and not old_font.is_variable():
            self.instances()
            new_font.set_variations_from_static_font(old_font)
        # We want to match two static fonts which may have different styles,
        # hence why we override the wght value.
        elif not old_font.is_variable() and not new_font.is_variable():
            self.old_styles.append(Style(old_font, {"wght": 400}, ""))
            self.new_styles.append(Style(new_font, {"wght": 400}, ""))

    def instances(self, filter_styles=None):
        old_styles = {s.name: s for s in get_font_styles(self.old_fonts, "instances", filter_styles)}
        new_styles = {s.name: s for s in get_font_styles(self.new_fonts, "instances", filter_styles)}

        matching = set(old_styles.keys()) & set(new_styles.keys())
        self.old_styles = sorted([old_styles[s] for s in matching], key=lambda k: k.name)
        self.new_styles = sorted([new_styles[s] for s in matching], key=lambda k: k.name)

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
        if len(self.old_fonts) == 1 and len(self.new_fonts) == 1:
            scale_upem(self.old_fonts[0].ttFont, self.new_fonts[0].ttFont["head"].unitsPerEm)
            return
        assert self.old_styles + self.new_styles, "match styles first!"
        seen = set()
        for old_style, new_style in zip(self.old_styles, self.new_styles):
            if old_style in seen:
                continue
            scale_upem(old_style.font.ttFont, new_style.font.ttFont["head"].unitsPerEm)
            seen.add(old_style)
