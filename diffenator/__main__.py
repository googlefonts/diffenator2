#!/usr/bin/env python3
"""
diffenator2
"""
from diffenator import DiffFonts, Reporter
from diffenator.font import DFont, match_fonts
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("old_font")
    parser.add_argument("new_font")
    parser.add_argument("--strings", help="File of strings to visually compare")
    parser.add_argument("--out", "-o", default="out", help="Output html path")
    args = parser.parse_args()

    old_font = DFont(args.old_font)
    new_font = DFont(args.new_font)
    old_font, new_font = match_fonts(old_font, new_font, scale_upm=True)

    diff = DiffFonts(old_font, new_font)
    diff.diff_all()
    if args.strings:
        diff.diff_strings(args.strings)

    report = Reporter(diff)
    report.save(args.out)


if __name__ == "__main__":
    main()
