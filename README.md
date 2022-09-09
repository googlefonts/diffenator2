# Diffenator 2

Compare two fonts

**Warning**

This tool is under active development so it doesn't have a stable api. Expect to see different results when updating the tool as M Foley may be playing around with thresholds etc.

In order to compare fonts, we compare them against real words. These word lists have been constructed from wikipedia dumps e.g https://archive.org/download/hiwiki-20210201. You will want to use the articles .xml dump e.g hiwiki-20210201-pages-articles.xml.bz2


This repo will eventually be moved to `googlefonts` once we hit a level of quality that the team is happy with. 


## Installing

`pip install git+https://github.com/m4rc1e/diffenator2`

## Comparing two fonts

`diffenator font1.ttf font2.ttf -o out_dir`

## Generating a wordlist

`python diffenator/shape.py build path_to_wikipedia.xml diffenator/data/wordlists/wordlist.txt --glyphs="acbdefghijkln..."`


`--glyphs` specifies what glyphs are allowed in a word.