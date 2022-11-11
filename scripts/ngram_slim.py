from diffenator.wordlistbuilder import maybe_add_word


def slim_file(file, size=None):
    with open(file) as doc:
        words = []
        for line in doc:
            word = line.strip()
            words.append(word)

    while True:
        print(f"Crunching wordlist {file}; current length={len(words)}")
        bank = set()
        ngram_auto = set()
        for word in sorted(words, key=lambda x: -len(x)):
            maybe_add_word(bank, word, ngram_auto, size=size)
        if len(bank) == len(words):
            break
        words = bank

    with open(file, "w", encoding="utf8") as doc:
        doc.write("\n".join(sorted(bank)))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Slim a wordlist file")
    parser.add_argument("files", metavar="FILE", nargs="+")
    parser.add_argument("--ngram-size", dest="size", type=int, default=None)

    args = parser.parse_args()
    for file in args.files:
        slim_file(file, args.size)
