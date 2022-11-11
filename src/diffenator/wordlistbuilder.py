import argparse
from collections import defaultdict

import ahocorasick


NGRAM_SIZE = 4


def all_ngrams(word):
    for i in range(len(word)-NGRAM_SIZE):
        yield word[i:i+NGRAM_SIZE]


def maybe_add_word(bank, word, ngram_auto, keep_chars: set[str]=None):
    if word in bank:
      return False

    if keep_chars and not all(c in keep_chars for c in word):
      return False

    if all(ngram in ngram_auto for ngram in all_ngrams(word)):
      return False

    bank.add(word)

    for ngram in all_ngrams(word):
        ngram_auto.add_word(ngram, ngram)
    return True


def build_words(fps: list[str], out: str, keep_chars: set[str]=None):
    keep_chars |= set("'")  # used for quoting obscure words in wikipedia
    bank = set()
    seen_keep_chars = set()
    ngram_auto = ahocorasick.Automaton()
    for fp in fps:
        with open(fp) as doc:
            # This is memory effecient. We do not want to use doc.read()
            # since this will try and load the whole file into memory
            for line in doc:
                words = line.split()
                for word in words:
                    word = word.replace("'", "")  # remove the quote marks
                    if maybe_add_word(bank, word, ngram_auto, keep_chars):
                        seen_keep_chars |= set(word)

    unseen_keep_chars = keep_chars - seen_keep_chars
    unseen_count = len(unseen_keep_chars)
    print(
        f"Following {unseen_count}/{len(keep_chars)} characters not seen in any words {unseen_keep_chars}."
    )

    words = remove_substring_words(bank)
    res = set()
    for word in words:
        # if word_freq[word] <= 2:
        #    continue
        res.add(word)
    with open(out, "w", encoding="utf8") as doc:
        doc.write("\n".join(res))


def remove_substring_words(words:set[str]) -> set[str]:
    res = set()
    auto = ahocorasick.Automaton()
    for word in sorted(words, key=lambda w: -len(w)):
        auto.add_word(word, word)
        res.add(word)
    auto.make_automaton()

    for word in words:
        for end_ind, found in auto.iter(word):
            if word != found:
                try:
                    res.remove(found)
                except:
                    all
    return res



def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True, dest="cmd")

    build = subparsers.add_parser("build")
    build.add_argument(
        "input_files", nargs="+", help="Text files to extract words from"
    )
    build.add_argument("--glyphs", "-g", required=True)
    build.add_argument("-o", "--out", default="out.txt")

    args = parser.parse_args()

    if args.cmd == "build":
        glyphs = None if not args.glyphs else set(args.glyphs)
        build_words(args.input_files, args.out, glyphs)
    else:
        raise ValueError(f"{args.cmd} unsupported command")


if __name__ == "__main__":
    main()
