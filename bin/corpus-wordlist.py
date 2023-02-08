"""
Convert https://github.com/google/corpuscrawler download files into
wordlists

Usage:
python bin/corpus-wordlist.py url out
python bin/corpus-wordlist.py http://www.gstatic.com/i18n/corpora/wordcounts/ach.txt Acoli.txt
"""
import argparse
import requests
from diffenator2.wordlistbuilder import remove_substring_words


def make_corpus_wordlist(string):
    lines = string.split("\n")
    words = set()
    import pdb
    pdb.set_trace()
    for line in lines:
        try:
            _, word = line.split("\t")
        except:
            print(f"cannot parse line '{line}'")
        words.add(word)
    words = remove_substring_words(words)
    return words


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("out")
    args = parser.parse_args()

    r = requests.get(args.url)
    words = r.text
    import pdb
    pdb.set_trace()

    words = make_corpus_wordlist(words)
    with open(args.out, "w") as out_doc:
        out_doc.write("\n".join(words))

if __name__ == "__main__":
    main()