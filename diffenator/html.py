import os
import logging


__all__ = [
    "CSSElement",
    "css_font_class_from_static",
    "css_font_classes_from_vf",
    "css_font_faces",
    "css_font_classes",
    "HtmlTemplater",
    "HtmlProof",
    "HtmlDiff",
    "simple_server",
    "daemon_server",
    "browserstack_local",
    "css_font_weight",
]


log = logging.getLogger("gftools.html")
log.setLevel(logging.INFO)


WIDTH_CLASS_TO_CSS = {
    1: "50%",
    2: "62.5%",
    3: "75%",
    4: "87.5%",
    5: "100%",
    6: "112.5%",
    7: "125%",
    8: "150%",
    9: "200%",
}


class CSSElement(object):
    """Create a CSSElement. CSSElements include a render method which
    renders the class as a string so it can be used in html templates.

    Args:
      selector: The css selector e.g h1, h2, class-name, @font0face
      **kwargs: css properties and their property values e.g
        font_family="MyFamily"

    Example:
      | >>> bold = CSSElement("bold", font_weight=700, font_style="normal")
      | >>> bold.render()
      | >>> 'bold { font-weight: 700; font-style: normal; }'
    """

    def __init__(self, selector, **kwargs):
        self.selector = selector
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.declerations = {k.replace("_", "-"): v for k, v in kwargs.items()}

    def render(self):
        decleration_strings = " ".join(
            f"{k}: {v};" for k, v in self.declerations.items() if not k.startswith("-")
        )
        return f"{self.selector} {{ { decleration_strings } }}"


def css_font_faces(ttFonts, server_dir=None, position=None):
    """Generate @font-face CSSElements for a collection of fonts

    Args:
      ttFonts: a list containing ttFont instances
      server_dir: optional. A path to the root directory of the server.
        @font-face src urls are relative to the server's root dir.
      position: optional. Adds a suffix to the font-family name

    Returns:
      A list of @font-face CSSElements
    """
    results = []
    for ttFont in ttFonts:
        family_name = (
            ttFont["name"].getName(16, 3, 1, 0x409)
            or ttFont["name"].getName(1, 3, 1, 0x409)
        ).toUnicode()
        style_name = (
            ttFont["name"].getName(2, 3, 1, 0x409)
            or ttFont["name"].getName(17, 3, 1, 0x409)
        ).toUnicode()
        font_path = ttFont.reader.file.name
        path = (
            font_path
            if not server_dir
            else os.path.relpath(font_path, start=server_dir)
        )
        src = f"url({path})"
        font_family = _class_name(family_name, style_name, position)
        font_style = (
            "italic"
            if ttFont["name"].getName(2, 3, 1, 0x409).toUnicode() == "Italic"
            else "normal"
        )
        font_weight = css_font_weight(ttFont)
        font_stretch = WIDTH_CLASS_TO_CSS[ttFont["OS/2"].usWidthClass]

        if "fvar" in ttFont:
            fvar = ttFont["fvar"]
            axes = {a.axisTag: a for a in fvar.axes}
            if "wght" in axes:
                min_weight = int(axes["wght"].minValue)
                max_weight = int(axes["wght"].maxValue)
                font_weight = f"{min_weight} {max_weight}"
            if "wdth" in axes:
                min_width = int(axes["wdth"].minValue)
                max_width = int(axes["wdth"].maxValue)
                font_stretch = f"{min_width}% {max_width}%"
            if "ital" in axes:
                pass
            if "slnt" in axes:
                min_angle = int(axes["slnt"].minValue)
                max_angle = int(axes["slnt"].maxValue)
                font_style = f"oblique {min_angle}deg {max_angle}deg"

        font_face = CSSElement(
            "@font-face",
            src=src,
            font_family=font_family,
            font_weight=font_weight,
            font_stretch=font_stretch,
            font_style=font_style,
        )
        results.append(font_face)
    return results


def css_font_classes(ttFonts, position=None):
    """Generate class CSSElements for a collection of fonts

    Args:
      ttFonts: a list containing ttFont instances
      position: optional. Adds a suffix to the font-family name

    Returns:
      A list of class CSSElements
    """
    results = []
    for ttFont in ttFonts:
        if "fvar" in ttFont:
            results += css_font_classes_from_vf(ttFont, position)
        else:
            results.append(css_font_class_from_static(ttFont, position))
    return results


def _class_name(family_name, style_name, position=None):
    string = f"{family_name}-{style_name}".replace(" ", "-")
    return string if not position else f"{string}-{position}"


def css_font_weight(ttFont):
    # At Google Fonts, we released many Thin families with a weight class of
    # 250. This was implemented to fix older GDI browsers
    weight = ttFont["OS/2"].usWeightClass
    return weight if weight != 250 else 100


def css_font_class_from_static(ttFont, position=None):
    family_name = (
        ttFont["name"].getName(16, 3, 1, 0x409)
        or ttFont["name"].getName(1, 3, 1, 0x409)
    ).toUnicode()
    style_name = (
        ttFont["name"].getName(2, 3, 1, 0x409)
        or ttFont["name"].getName(17, 3, 1, 0x409)
    ).toUnicode()

    class_name = _class_name(family_name, style_name, position)
    font_family = class_name
    font_weight = css_font_weight(ttFont)
    font_style = (
        "italic"
        if ttFont["name"].getName(2, 3, 1, 0x409).toUnicode() == "Italic"
        else "normal"
    )
    font_stretch = WIDTH_CLASS_TO_CSS[ttFont["OS/2"].usWidthClass]
    return CSSElement(
        class_name,
        _full_name=f"{family_name} {style_name}",
        _style=style_name,
        _font_path=ttFont.reader.file.name,
        font_family=font_family,
        font_weight=font_weight,
        font_style=font_style,
        font_stretch=font_stretch,
    )


def css_font_classes_from_vf(ttFont, position=None):
    instances = ttFont["fvar"].instances
    nametable = ttFont["name"]
    family_name = (
        ttFont["name"].getName(16, 3, 1, 0x409)
        or ttFont["name"].getName(1, 3, 1, 0x409)
    ).toUnicode()
    style_name = (
        ttFont["name"].getName(2, 3, 1, 0x409)
        or ttFont["name"].getName(17, 3, 1, 0x409)
    ).toUnicode()

    results = []
    for instance in instances:
        nameid = instance.subfamilyNameID
        inst_style = nametable.getName(nameid, 3, 1, 0x409).toUnicode()

        class_name = _class_name(family_name, inst_style, position)
        font_family = _class_name(family_name, style_name, position)
        font_weight = (
            css_font_weight(ttFont)
            if not "wght" in instance.coordinates
            else int(instance.coordinates["wght"])
        )
        font_style = "italic" if "Italic" in inst_style else "normal"
        font_stretch = (
            "100%"
            if not "wdth" in instance.coordinates
            else f"{int(instance.coordinates['wdth'])}%"
        )
        font_class = CSSElement(
            class_name,
            _full_name=f"{family_name} {inst_style}",
            _style=inst_style,
            _font_path=ttFont.reader.file.name,
            font_family=font_family,
            font_weight=font_weight,
            font_style=font_style,
            font_stretch=font_stretch,
        )
        results.append(font_class)
    return results
