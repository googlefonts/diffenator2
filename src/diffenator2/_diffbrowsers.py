#!/usr/bin/env python3
from __future__ import annotations
from pkg_resources import resource_filename
from diffenator2.html import proof_rendering, diff_rendering
from diffenator2.font import DFont, get_font_styles
from diffenator2.matcher import FontMatcher
from diffenator2.utils import re_filter_characters
from glob import glob
import os
import fire


def main2(**kwargs):
    # populate default args
    styles = kwargs.get("styles", "instances")
    filter_styles = kwargs.get("filter_styles", ".*")
    characters = kwargs.get("characters", ".*")
    out = kwargs.get("out", "out")
    pt_size = int(kwargs.get("pt_size", "14"))
    templates = kwargs.get("templates", glob(
            os.path.join(
                resource_filename("diffenator2", "templates"), "diffbrowsers*.html"
            )
        ),)

    if "proof" in kwargs:
        fonts = [DFont(os.path.abspath(fp)) for fp in kwargs["fonts"]]
        styles = get_font_styles(fonts, styles, filter_styles)

        characters = re_filter_characters(fonts[0], characters)
        proof_rendering(
            styles,
            templates,
            out,
            filter_styles=filter_styles,
            characters=characters,
            pt_size=pt_size,
        )

    elif "diff" in kwargs:
        fonts_before = [DFont(os.path.abspath(fp), suffix="old") for fp in kwargs["fonts_before"]]
        fonts_after = [DFont(os.path.abspath(fp), suffix="new") for fp in kwargs["fonts_after"]]
        matcher = FontMatcher(fonts_before, fonts_after)
        getattr(matcher, styles)(filter_styles)
        characters = re_filter_characters(fonts_before[0], characters)
        diff_rendering(
            matcher,
            templates,
            out,
            filter_styles=filter_styles,
            characters=characters,
            pt_size=pt_size,
        )
    else:
        raise ValueError("Provide either --diff=True or --proof=True")

    if "imgs" in kwargs:
        imgs_out = os.path.join(out, "imgs")
        from diffenator2.screenshot import screenshot_dir
        screenshot_dir(out, imgs_out)


def main():
    # we cannot use this under if __name__ == "__main__"
    # https://github.com/google/python-fire/issues/103
    fire.Fire(main2)


if __name__ == "__main__":
    main()
