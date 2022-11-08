import requests
from gflanguages import LoadLanguages
# archive.org has the wikipedia dumps
# https://en.wikipedia.org/wiki/Wikipedia:Database_download#Where_do_I_get_it?
PAGE_URL = "https://archive.org/details/{}wiki-20220201"
DL_URL = "https://archive.org/download/glwiki-20220201/{}wiki-20220201-pages-articles.xml.bz2"

from gflanguages import LoadScripts

scripts = LoadScripts()


def wordlist_for(script):
    languages = LoadLanguages()
    for _, lang in languages.items():
        if lang.population < 2000000:
            continue
        print(lang.name, lang.language, scripts[lang.script].name, lang.script)

        wiki_url = PAGE_URL.format(lang.language)
        #if requests.get(wiki_url).status_code != 200:
        #    continue
        #import pdb
        #pdb.set_trace()


wordlist_for("Latin", )