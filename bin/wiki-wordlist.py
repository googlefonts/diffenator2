"""
Script to build wordlists from wikipedia dumps
"""
import os
import requests
from gflanguages import LoadLanguages, LoadScripts
from functools import lru_cache
from diffenator.utils import download_file
from diffenator.wordlistbuilder import build_words
import tempfile
import bz2
import argparse
import logging

log = logging.getLogger(__name__)


# archive.org has the wikipedia dumps
# https://en.wikipedia.org/wiki/Wikipedia:Database_download#Where_do_I_get_it?
PAGE_URL = "https://archive.org/details/{}wiki-20220201"
DL_URL = "https://archive.org/download/{}wiki-20220201/{}wiki-20220201-pages-articles.xml.bz2"

SCRIPTS = LoadScripts()
LANGUAGES = LoadLanguages()


@lru_cache()
def langs_in_script(script: str) -> list[str]:
    results = []
    for _, lang in LANGUAGES.items():
        if lang.script not in SCRIPTS:
            continue
        lang_script = SCRIPTS[lang.script]
        if lang.population < 2000000 or lang_script.name != script:
            continue
        results.append(lang)
    return results


def download_urls(script: str) -> list[str]:
    results = []
    langs = langs_in_script(script)
    for lang in langs:
        wiki_url = PAGE_URL.format(lang.language)
        if requests.get(wiki_url).status_code != 200:
            continue
        results.append(DL_URL.format(lang.language, lang.language))
    return results


def _parse_string(string: str) -> set[str]:
    results = set()
    for i in string.split():
        if i.startswith("{") and i.endswith("}"):
            results.add(i[1:-1])
        else:
            results.add(i)
    return results


def characters(script: str) -> set[str]:
    results = set()
    langs = langs_in_script(script)
    for lang in langs:
        if not hasattr(lang, "exemplar_chars"):
            continue
        characters = lang.exemplar_chars
        if hasattr(characters, "base"):
            results |= _parse_string(characters.base)
        if hasattr(characters, "mark"):
            results |= _parse_string(characters.marks)
        if hasattr(characters, "auxiliary"):
            results |= _parse_string(characters.auxiliary)
    results |= set(c.upper() for c in results)
    return results


def has_script(script: str) -> bool:
    known_scripts = sorted([SCRIPTS[s].name for s in SCRIPTS.keys()])
    if script not in known_scripts:
        raise ValueError(f"'{script}' not found. Choose from {known_scripts}")
    return True


def download_xml_files(dl_urls: list[str], dst_dir: str) -> list[str]:
    results = []
    for url in dl_urls:
        dst = os.path.join(dst_dir, os.path.basename(url))
        download_file(url, dst)
        zipfile = bz2.BZ2File(dst)
        newdst = dst[:-4]
        results.append(newdst)
        with open(newdst, "wb") as doc:
            doc.write(zipfile.read())
    return results


def make_wiki_wordlist(script: str, out: str):
    has_script(script)
    log.info("Finding wikidump download urls.")
    dl_urls = download_urls(script)
    log.debug(f"Found wiki dump urls {dl_urls} for '{script}' script")
    chars = characters(script)
    log.debug(f"Following characters are used in the script: {chars}")

    log.info(f"Downloading and extracting {dl_urls}.")
    with tempfile.TemporaryDirectory() as tmp_dir:
        xml_files = download_xml_files(dl_urls, tmp_dir)
        log.info("building wordlist")
        build_words(xml_files, out, set("".join(chars)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("script")
    parser.add_argument("out")
    parser.add_argument("-v", "--verbose", help="verbose", action="store_true", default=False)
    args = parser.parse_args()

    logging.basicConfig(level="DEBUG" if args.verbose else "INFO", format="%(name)s: %(levelname)s: %(message)s")
    make_wiki_wordlist(args.script, args.out)


if __name__ == "__main__":
    main()