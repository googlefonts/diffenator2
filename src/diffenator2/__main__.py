#!/usr/bin/env python3
from __future__ import annotations
from argparse import ArgumentParser, Namespace
import os
from diffenator2 import ninja_diff, ninja_proof, THRESHOLD, NINJA_BUILD_FILE
from diffenator2.font import DFont
from diffenator2.html import build_index_page
from diffenator2.renderer import FONT_SIZE



def main(**kwargs):
    if kwargs:
        args = Namespace(**kwargs)
    else:
        parser = ArgumentParser()
        subparsers = parser.add_subparsers(
            dest="command", required=True, metavar='"proof" or "diff"'
        )
        universal_options_parser = ArgumentParser(add_help=False)
        universal_options_parser.add_argument(
            "--out", "-o", help="Output dir", default="out"
        )
        universal_options_parser.add_argument(
            "--imgs", help="Generate images", action="store_true", default=False
        )
        universal_options_parser.add_argument("--filter-styles", default=None)
        universal_options_parser.add_argument("--characters", "-ch", default=".*")
        universal_options_parser.add_argument("--pt-size", "-pt", default=20)
        universal_options_parser.add_argument("--templates")
        universal_options_parser.add_argument(
            "--styles", "-s", choices=("instances", "cross_product", "masters"),
            default="instances",
            help="Show font instances, cross product or master styles"
        )
        universal_options_parser.add_argument("--user-wordlist", default=None)
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
        diff_parser.add_argument("--no-diffenator", default=False, action="store_true")
        diff_parser.add_argument("--threshold", "-t", type=float, default=THRESHOLD)
        diff_parser.add_argument("--precision", default=FONT_SIZE)
        diff_parser.add_argument("--no-tables", action="store_true", help="Skip diffing font tables")
        diff_parser.add_argument("--no-words", action="store_true", help="Skip diffing wordlists")
        args = parser.parse_args()

    if args.command == "proof":
        ninja_proof(**vars(args))
    elif args.command == "diff":
        args.fonts_before = [DFont(f) for f in args.fonts_before]
        args.fonts_after = [DFont(f) for f in args.fonts_after]
        ninja_diff(**vars(args))
    else:
        raise NotImplementedError(f"{args.command} not supported")
    # TODO (Marc F) find a better home for this when refactoring
    build_index_page(args.out)


if __name__ == "__main__":
    main()
