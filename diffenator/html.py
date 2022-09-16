from fontTools.ttLib import TTFont
from pkg_resources import resource_filename
from jinja2 import Environment, FileSystemLoader, select_autoescape
import tempfile
import os
from multiprocessing import Process
from contextlib import contextmanager
from http.server import *
import logging
import time
from copy import copy
import shutil
from collections import namedtuple
from diffenator.utils import *


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
        family_name = font_familyname(ttFont)
        style_name = font_stylename(ttFont)
        font_path = ttFont.reader.file.name
        path = (
            font_path
            if not server_dir
            else os.path.relpath(font_path, start=server_dir)
        )
        src = f"url({path})"
        font_family = _class_name(family_name, style_name, position)
        font_style = "italic" if font_is_italic(ttFont) else "normal"
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
    family_name = font_familyname(ttFont)
    style_name = font_stylename(ttFont)

    class_name = _class_name(family_name, style_name, position)
    font_family = class_name
    font_weight = css_font_weight(ttFont)
    font_style = "italic" if font_is_italic(ttFont) else "normal"
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
    family_name = font_familyname(ttFont)
    style_name = font_stylename(ttFont)

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


Document = namedtuple("Document", ["filename", "path", "options"])


class HtmlTemplater(object):

    def __init__(
        self,
        out="out",
        template_dir=resource_filename("diffenator", "templates"),
    ):
        """
        Generate html documents from Jinja2 templates and optionally
        screenshot the results on different browsers, using the
        Browserstack Screenshot api.

        When saving images, two brackground processes are started. A local
        server which serves the populated html documents
        and browserstack local. This allows Browserstack to take local
        screenshots.

        The main purpose of this class is to allow developers to
        write their own template generators by using inheritance e.g

        ```
        class MyTemplate(HtmlTemplater):
            def __init__(self, forename, surname, out):
                super().__init__(self, out)
                self.forename = forename
                self.surname = surname

        html = MyTemplate("Joe", "Doe")
        html.build_pages()
        ```

        template:
        <p>Hello {{ forename }} {{ surname }}.</p>

        result:
        <p>Hello Joe Doe.</p>

        For more complex examples, see HtmlProof and HtmlDiff in this
        module.

        All html docs and assets are saved into the specified out
        directory. Packaging the assets together makes it easier to share
        and we don't have to worry about absolute vs relative paths. This
        can be problematic for some assets such as webfonts where the path
        must be related to the local server, not the user's system.

        Note: Templates whose filename's start with an "_" are non
        renderable. This functionality exists so css classes etc
        can be defined in a _base.html file which other templates can
        inherit from.

        Args:
          out: output dir for generated html documents
          template_dir: the directory containing the html templates
          browserstack_username: optional. Browserstack username
          browserstack_access_key: optional. Browserstack access key
          browserstack_config: optional. Browserstack config file. See
            api docs for more info:
            https://www.browserstack.com/screenshots/api
        """
        self.template_dir = template_dir
        self.templates = [
            f
            for f in os.listdir(os.path.join(self.template_dir, "diffbrowsers"))
            if all([not f.startswith("_"), f.endswith("html")])
        ]
        # TODO we may want to make this an arg
        self.server_url = "http://0.0.0.0:8000"
        self.jinja = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        self.out = self.mkdir(out)
        self.documents = {}
        # Set to true if html pages are going get cropped in Browserstack

    def build_pages(self, pages=None, dst=None, **kwargs):
        if not pages:
            pages = self.templates
        log.info(f"Building pages {pages}")
        for page in pages:
            self.build_page(page, dst=dst, **kwargs)

    def build_page(self, filename, dst=None, **kwargs):
        if not "pt_size" in kwargs:
            kwargs["pt_size"] = 14
        # Combine self.__dict__ attributes with function kwargs. This allows Jinja
        # templates to access the class attributes
        jinja_kwargs = {**self.__dict__, **kwargs}
        out = self._render_html(filename, dst=dst, **jinja_kwargs)
        self.documents[filename] = Document(filename, out, kwargs)

    def _render_html(self, filename, dst=None, **kwargs):
        html_template = self.jinja.get_template("diffbrowsers/" + filename)
        html = html_template.render(**kwargs)
        dst = dst if dst else os.path.join(self.out, filename)
        with open(dst, "w") as html_file:
            html_file.write(html)
        return dst

    def mkdir(self, path):
        if not os.path.isdir(path):
            os.mkdir(path)
        return path

    def copy_files(self, srcs, dst):
        [shutil.copy(f, dst) for f in srcs]
        return [os.path.join(dst, os.path.basename(f)) for f in srcs]

    def save_imgs(self, pages=None, dst=None):
        assert hasattr(self, "screenshot")

        pages = pages if pages else self.documents.keys()
        log.warning("Generating images with Browserstack. This may take a while")
        img_dir = dst if dst else self.mkdir(os.path.join(self.out, "img"))
        with daemon_server(directory=self.out):
            for page in pages:
                if page not in self.documents:
                    raise ValueError(
                        f"{page} doesn't exist in documents, '{self.documents}'"
                    )
                paths = self.documents[page].path
                out = os.path.join(img_dir, page)
                self.mkdir(out)
                self._save_img(paths, out)

    def _save_img(self, path, dst):
        pass
        #page = os.path.relpath(path, start=self.out)
        #url = f"{self.server_url}/{page}"
        #self.screenshot.take(url, dst)


class HtmlProof(HtmlTemplater):
    def __init__(
        self, fonts, out="out", template_dir=resource_filename("diffenator", "templates")
    ):
        """Proof a single family."""
        super().__init__(out, template_dir=template_dir)
        fonts_dir = os.path.join(out, "fonts")
        self.mkdir(fonts_dir)

        self.fonts = self.copy_files(fonts, fonts_dir)
        self.ttFonts = [TTFont(f) for f in self.fonts]

        self.css_font_faces = css_font_faces(self.ttFonts, self.out)
        self.css_font_classes = css_font_classes(self.ttFonts)

        self.sample_text = "Hello world"
        self.glyphs = "A B C D E F G H I J K L"


class HtmlDiff(HtmlTemplater):
    def __init__(
        self,
        fonts_before,
        fonts_after,
        out="out",
        template_dir=resource_filename("diffenator", "templates"),
    ):
        """Compare two families"""
        super().__init__(out=out, template_dir=template_dir)
        fonts_before_dir = os.path.join(out, "fonts_before")
        fonts_after_dir = os.path.join(out, "fonts_after")
        self.mkdir(fonts_before_dir)
        self.mkdir(fonts_after_dir)

        self.fonts_before = self.copy_files(fonts_before, fonts_before_dir)
        self.ttFonts_before = [TTFont(f) for f in self.fonts_before]

        self.fonts_after = self.copy_files(fonts_after, fonts_after_dir)
        self.ttFonts_after = [TTFont(f) for f in self.fonts_after]

        self.css_font_faces_before = css_font_faces(
            self.ttFonts_before, self.out, position="before"
        )
        self.css_font_faces_after = css_font_faces(
            self.ttFonts_after, self.out, position="after"
        )

        self.css_font_classes_before = css_font_classes(self.ttFonts_before, "before")
        self.css_font_classes_after = css_font_classes(self.ttFonts_after, "after")
        self._match_css_font_classes()

        self.too_big_for_browserstack = len(self.css_font_classes_before) > 4

        self.sample_text = " ".join(font_sample_text(self.ttFonts_before[0]))
        self.glyphs = get_encoded_glyphs(self.ttFonts_before[0])

    def _match_css_font_classes(self):
        """Match css font classes by full names for static fonts and
        family name + instance name for fvar instances"""
        styles_before = {s._full_name: s for s in self.css_font_classes_before}
        styles_after = {s._full_name: s for s in self.css_font_classes_after}
        shared_styles = set(styles_before) & set(styles_after)

        self.css_font_classes_before = sorted(
            [s for k, s in styles_before.items() if k in shared_styles],
            key=lambda s: (s.font_weight, s._full_name),
        )
        self.css_font_classes_after = sorted(
            [s for k, s in styles_after.items() if k in shared_styles],
            key=lambda s: (s.font_weight, s._full_name),
        )
        if not all([self.css_font_classes_before, self.css_font_classes_after]):
            raise ValueError("No matching fonts found")

    def _render_html(
        self,
        filename,
        **kwargs,
    ):
        html_template = self.jinja.get_template(filename)

        # This document is intended for humans. It includes a button
        # to toggle which set of fonts is visible.
        combined = html_template.render(include_ui=True, **kwargs)
        combined_path = os.path.join(self.out, filename)
        with open(combined_path, "w") as combined_html:
            combined_html.write(combined)

        # This document contains fonts_before. It solely exists for
        # screenshot generation purposes
        before_kwargs = copy(kwargs)
        before_kwargs.pop("css_font_classes_after")
        before = html_template.render(**before_kwargs)
        before_filename = f"{filename[:-5]}-before.html"
        before_path = os.path.join(self.out, before_filename)
        with open(before_path, "w") as before_html:
            before_html.write(before)

        # This document contains fonts_after. It solely exists for
        # screenshot generation purposes
        after_kwargs = copy(kwargs)
        after_kwargs.pop("css_font_classes_before")
        after = html_template.render(**after_kwargs)
        after_filename = f"{filename[:-5]}-after.html"
        after_path = os.path.join(self.out, after_filename)
        with open(after_path, "w") as after_html:
            after_html.write(after)

        return (before_path, after_path)

    def _save_img(self, document, dst):
        # Output results as a gif
        before_page = os.path.relpath(document[0], start=self.out)
        after_page = os.path.relpath(document[1], start=self.out)
        before_url = f"{self.server_url}/{before_page}"
        after_url = f"{self.server_url}/{after_page}"
        with tempfile.TemporaryDirectory() as before_dst, tempfile.TemporaryDirectory() as after_dst:
            self.screenshot.take(before_url, before_dst)
            self.screenshot.take(after_url, after_dst)
            gen_gifs(before_dst, after_dst, dst)


# Local server functions


def simple_server(directory="."):
    """A simple python web server which can be served from a specific
    directory

    Args:
      directory: start the server from a specified directory. Default is cwd
    """

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

    server_address = ("", 8000)
    httpd = HTTPServer(server_address, Handler)
    httpd.serve_forever()


@contextmanager
def daemon_server(directory="."):
    """Start a simple_server as a background process.

    Args:
      directory: start the server from a specified directory. Default is '.'
    """
    p = Process(target=simple_server, args=[directory], daemon=True)
    try:
        p.start()
        yield p
    finally:
        p.terminate()


