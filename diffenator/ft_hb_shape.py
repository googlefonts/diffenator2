import logging
from blackrenderer.render import renderText

logger = logging.getLogger(__name__)



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Draw some text")
    parser.add_argument("font", metavar="TTF")
    parser.add_argument("string", metavar="TEXT")
    parser.add_argument("--out", "-o", metavar="PNG", default="out.png")
    parser.add_argument("--lang", metavar="LANGUAGE")
    parser.add_argument("--script", metavar="SCRIPT")
    parser.add_argument("--features", metavar="FEATURES")
    args = parser.parse_args()
    features = None
    if args.features:
        features = {}
        for f in args.features.split(","):
            if f[0] == "-":
                features[f[1:]] = False
            elif f[0] == "+":
                features[f[1:]] = True
            else:
                features[f] = True

    renderText(args.font, args.string, args.out, features=features, lang=args.lang, script=args.script)
