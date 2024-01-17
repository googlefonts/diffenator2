#!/usr/bin/env python3
from __future__ import annotations
from pkg_resources import resource_filename
from diffenator2.html import proof_rendering, diff_rendering
from diffenator2.font import DFont, get_font_styles
from diffenator2.matcher import FontMatcher
from diffenator2.utils import re_filter_characters
from glob import glob
import os
import sys
import ast
import types
import tempfile
import shutil


def _get_diffbrowser_templates(user_templates, out):
    existing_templates = glob(
        os.path.join(resource_filename("diffenator2", "templates"), "*.html")
    )
    for fp in user_templates:
        if not fp.startswith("diffbrowsers"):
            dst_filename = "diffbrowsers_" + os.path.basename(fp)
        else:
            dst_filename = os.path.basename(fp)
        shutil.copy(fp, os.path.join(out, dst_filename))

    for fp in existing_templates:
        shutil.copy(fp, os.path.join(out, os.path.basename(fp)))
    return glob(os.path.join(out, "diffbrowsers*.html"))


def main():
    # Maybe json load/dump is better
    args = types.SimpleNamespace(**ast.literal_eval(sys.argv[1]))

    with tempfile.TemporaryDirectory() as tmp_dir:
        templates = _get_diffbrowser_templates(args.diffbrowsers_templates, tmp_dir)

        if args.command == "proof":
            fonts = [DFont(os.path.abspath(fp)) for fp in args.fonts]
            styles = get_font_styles(fonts, args.styles, args.filter_styles)

            characters = re_filter_characters(fonts[0], args.characters)
            proof_rendering(
                styles,
                templates,
                args.out,
                filter_styles=args.filter_styles,
                characters=characters,
                pt_size=args.pt_size,
                user_wordlist=args.user_wordlist,
            )

        elif args.command == "diff":
            fonts_before = [
                DFont(os.path.abspath(fp), suffix="old") for fp in args.fonts_before
            ]
            fonts_after = [
                DFont(os.path.abspath(fp), suffix="new") for fp in args.fonts_after
            ]
            matcher = FontMatcher(fonts_before, fonts_after)
            getattr(matcher, args.styles)(args.filter_styles)
            characters = re_filter_characters(fonts_before[0], args.characters)
            diff_rendering(
                matcher,
                templates,
                args.out,
                filter_styles=args.filter_styles,
                characters=characters,
                pt_size=args.pt_size,
                user_wordlist=args.user_wordlist,
            )

        if args.imgs:
            imgs_out = os.path.join(args.out, "imgs")
            from diffenator2.screenshot import screenshot_dir

            screenshot_dir(args.out, imgs_out)


if __name__ == "__main__":
    main()
