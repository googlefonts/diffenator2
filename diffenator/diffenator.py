#!/usr/bin/env python3
"""
diffenator2
"""
from diffenator import string_coords_to_dict
from diffenator.diff import DiffFonts
from diffenator.font import DFont, match_fonts
from pkg_resources import resource_filename
import os
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("old_font")
    parser.add_argument("new_font")
    parser.add_argument("--template", default=resource_filename("diffenator", os.path.join("templates", "diffenator.html")))
    parser.add_argument("--strings", help="File of strings to visually compare")
    parser.add_argument("--coords", "-c", default={})
    parser.add_argument("--out", "-o", default="out", help="Output html path")
    args = parser.parse_args()

    coords = string_coords_to_dict(args.coords)

    old_font = DFont(os.path.abspath(args.old_font))
    new_font = DFont(os.path.abspath(args.new_font))
    match_fonts(old_font, new_font, variations=coords, scale_upm=True)

    diff = DiffFonts(old_font, new_font)
    diff.diff_all()
    if args.strings:
        diff.diff_strings(args.strings)
    diff.to_html(args.template, args.out)


if __name__ == "__main__":
    main()
