#!/usr/bin/env python3
from __future__ import annotations
from argparse import ArgumentParser, Namespace
import os
from diffenator2 import ninja_diff, ninja_proof, THRESHOLD, NINJA_BUILD_FILE
from diffenator2.font import DFont
from diffenator2.html import build_index_page



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
        universal_options_parser.add_argument(
            "--styles", "-s", choices=("instances", "cross_product", "masters"),
            default="instances",
            help="Show font instances, cross product or master styles"
        )
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
        diff_parser.add_argument("--no-diffenator", default=False, action="store_true")
        diff_parser.add_argument("--threshold", "-t", type=float, default=THRESHOLD)
        args = parser.parse_args()

    if os.path.exists(NINJA_BUILD_FILE):
        os.remove(NINJA_BUILD_FILE)
    if os.path.exists(".ninja_log"):
        os.remove(".ninja_log")
    if args.command == "proof":
        fonts = [DFont(f) for f in args.fonts]
        ninja_proof(
            fonts,
            out=args.out,
            imgs=args.imgs,
            styles=args.styles,
            filter_styles=args.filter_styles,
            characters=args.characters,
            pt_size=args.pt_size,
        )
    elif args.command == "diff":
        fonts_before = [DFont(f) for f in args.fonts_before]
        fonts_after = [DFont(f) for f in args.fonts_after]
        ninja_diff(
            fonts_before,
            fonts_after,
            out=args.out,
            imgs=args.imgs,
            styles=args.styles,
            characters=args.characters,
            diffenator=False if args.no_diffenator else True,
            user_wordlist=args.user_wordlist,
            filter_styles=args.filter_styles,
            pt_size=args.pt_size,
            threshold=args.threshold,
        )
    else:
        raise NotImplementedError(f"{args.command} not supported")
    # TODO (Marc F) find a better home for this when refactoring
    build_index_page(args.out)


if __name__ == "__main__":
    main()
