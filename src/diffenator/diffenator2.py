#!/usr/bin/env python3
from __future__ import annotations
import argparse
from fontTools.ttLib import TTFont
from diffenator import ninja_diff, ninja_proof
import ninja


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="command", required=True, metavar='"proof" or "diff"'
    )
    universal_options_parser = argparse.ArgumentParser(add_help=False)
    universal_options_parser.add_argument(
        "--out", "-o", help="Output dir", default="out"
    )
    universal_options_parser.add_argument(
        "--imgs", help="Generate images", action="store_true", default=False
    )
    universal_options_parser.add_argument("--filter-styles", default=None)
    proof_parser = subparsers.add_parser(
        "proof",
        parents=[universal_options_parser],
        help="Generate html proofing documents for a family",
    )
    proof_parser.add_argument("fonts", nargs="+")

    diff_parser = subparsers.add_parser(
        "diff",
        parents=[universal_options_parser],
    )
    diff_parser.add_argument("--fonts-before", "-fb", nargs="+", required=True)
    diff_parser.add_argument("--fonts-after", "-fa", nargs="+", required=True)
    diff_parser.add_argument("--user-wordlist", default=None)

    args = parser.parse_args()

    if args.command == "proof":
        fonts = [TTFont(f) for f in args.fonts]
        ninja_proof(
            fonts, out=args.out, imgs=args.imgs, filter_styles=args.filter_styles
        )
    elif args.command == "diff":
        fonts_before = [TTFont(f) for f in args.fonts_before]
        fonts_after = [TTFont(f) for f in args.fonts_after]
        ninja_diff(
            fonts_before,
            fonts_after,
            out=args.out,
            imgs=args.imgs,
            user_wordlist=args.user_wordlist,
            filter_styles=args.filter_styles,
        )
    else:
        raise NotImplementedError(f"{args.command} not supported")
    ninja._program("ninja", [])


if __name__ == "__main__":
    main()
