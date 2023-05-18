#!/usr/bin/env python3
"""
gftools gen-html aka diffbrowsers2.

Generate html documents to proof a font family, or generate documents to
diff two families.

Examples:
# Generate proofing documents for a single font
gftools gen-html proof font1.ttf

# Generate proofing documents for a family of fonts
gftools gen-html proof font1.ttf font2.ttf font3.ttf

# Output test pages to a dir
gftools gen-html proof font1.ttf -o ~/Desktop/myFamily

# Generate proofing documents and output images using Browserstack
# (a subscription is required)
gftools gen-html proof font1.ttf --imgs

# Generate diff documents
gftools gen-html diff -fb ./fonts_before/font1.ttf -fa ./fonts_after/font1.ttf
"""
from __future__ import annotations
from pkg_resources import resource_filename
from diffenator2.html import proof_rendering, diff_rendering
from diffenator2.font import DFont, get_font_styles
from diffenator2.matcher import FontMatcher
from diffenator2.utils import re_filter_characters
from glob import glob
import os
import argparse


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="command", required=True, metavar='"proof" or "diff"'
    )

    # Optional args which can be used in all subparsers
    universal_options_parser = argparse.ArgumentParser(add_help=False)
    universal_options_parser.add_argument(
        "--styles", "-s", choices=("instances", "cross_product", "masters"),
        default="instances",
        help="Show font instances, cross product or master styles"
    )
    universal_options_parser.add_argument(
        "--pt-size", "-pt", help="Change pt size of document text", default=14
    )
    universal_options_parser.add_argument(
        "--out", "-o", help="Output dir", default="out"
    )
    universal_options_parser.add_argument(
        "--templates",
        help="HTML templates. By default, diffenator/templates/diffbrowsers_*.html is used.",
        default=glob(
            os.path.join(
                resource_filename("diffenator2", "templates"), "diffbrowsers*.html"
            )
        ),
    )
    universal_options_parser.add_argument(
        "--imgs", action="store_true", help="Generate images using headless browsers"
    )
    universal_options_parser.add_argument("--filter-styles", default=None)
    universal_options_parser.add_argument("--characters", "-ch", default=".*")

    proof_parser = subparsers.add_parser(
        "proof",
        parents=[universal_options_parser],
        help="Generate html proofing documents for a family",
    )
    proof_parser.add_argument("fonts", nargs="+")

    diff_parser = subparsers.add_parser(
        "diff",
        parents=[universal_options_parser],
        help="Generate html diff documents which compares two families. "
        "Variable fonts can be compared against static fonts because we "
        "match the fvar instances against the static fonts. To Match fonts "
        "we use the font's name table records. For static fonts, the fullname "
        "is used e.g 'Maven Pro Medium'. For variable fonts, the family name "
        "+ fvar instance subfamilyname is used e.g 'Maven Pro' + 'Medium'.",
    )
    diff_parser.add_argument("--fonts-before", "-fb", nargs="+", required=True)
    diff_parser.add_argument("--fonts-after", "-fa", nargs="+", required=True)

    args = parser.parse_args()

    if args.command == "proof":
        fonts = [DFont(os.path.abspath(fp)) for fp in args.fonts]
        styles = get_font_styles(fonts, args.styles, args.filter_styles)

        characters = re_filter_characters(fonts[0], args.characters)
        proof_rendering(
            styles,
            args.templates,
            args.out,
            filter_styles=args.filter_styles,
            characters=characters,
            pt_size=args.pt_size
        )

    elif args.command == "diff":
        fonts_before = [DFont(os.path.abspath(fp), suffix="old") for fp in args.fonts_before]
        fonts_after = [DFont(os.path.abspath(fp), suffix="new") for fp in args.fonts_after]
        matcher = FontMatcher(fonts_before, fonts_after)
        getattr(matcher, args.styles)(args.filter_styles)
        characters = re_filter_characters(fonts_before[0], args.characters)
        diff_rendering(
            matcher,
            args.templates,
            args.out,
            filter_styles=args.filter_styles,
            characters=characters,
            pt_size=args.pt_size,
        )

    if args.imgs:
        imgs_out = os.path.join(args.out, "imgs")
        from diffenator2.screenshot import screenshot_dir
        screenshot_dir(args.out, imgs_out)


if __name__ == "__main__":
    main()
