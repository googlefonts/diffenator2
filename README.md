# Diffenator 2

Compare two font families.

This tool primarily checks two font families for visual differences by comparing fonts against real words (wordlists can be found in the `src/diffenator/data/wordlists` directory). It also provides an improved "ttx diff" by treating each font as a tree and then doing a tree comparison. The output is a plain html file which then allows us to screenshot the differences using [Selenium](https://www.selenium.dev/documentation/webdriver/).

This tool replaces the original [fontdiffenator](https://github.com/googlefonts/fontdiffenator)


## Features

- Diff COLR v1 fonts (Uses [BlackRenderer](https://github.com/BlackFoundryCom/black-renderer))
- Diff fonts with different upms
- Diff fonts with different glyph names
- Diff static fonts against variable font fvar instances
- Diff variable font masters
- Diff variable font axes by using a cross product
- Output browser images using Selenium Webdriver
- Integrate into existing github action workflows by using the github action, https://github.com/f-actions/diffenator2
- Use [ninja](https://ninja-build.org/) to diff multiple fonts at the same time. Diffing all styles Noto Sans takes (XXXX)


## Install

`pip install git+https://github.com/googlefonts/diffenator2`

There's also a [github action](https://github.com/f-actions/diffenator2) for testing upstream font repositories.



## Caveats

Since we're comparing words, we cannot guarantee that abbreviations, names and optional OpenType features haven't regressed. In order to check these, users should create their own wordlist which contains the combinations they'd like to check. See Usage section for examples on how to do this.  

Words are compared by pixel diffing FreeType bitmaps at 3ppem. This size may sound too small, however M Foley's [tests](https://docs.google.com/document/d/16INOprdKWTZ4wyO41C0q4vuFpxFMO3Tod_Ig2sB4JAQ/edit?usp=sharing) show that it's still able to pick up incredibly small details. We include all pixel differences in the outputted reports (we will include threshold filtering soon). If you hover over each word, it will display an array which shows the pixel differences (0 no change, 255 max change).

In order to test fonts on the correct words, we first determine what scripts are supported within the font and then select the appropriate script specific wordlist. There are still a few scripts which we don't have wordlists for. Please ask M Foley to generate one if it's missing for your project.



## Usage

`diffenator2` has two subcommands, `diff` and `proof`.

### `diff`

```
usage: diffenator2 diff [-h] [--out OUT] [--imgs]
                        [--filter-styles FILTER_STYLES] [--pt-size PT_SIZE]
                        [--styles {instances,cross_product,masters}]
                        --fonts-before FONTS_BEFORE [FONTS_BEFORE ...]
                        --fonts-after FONTS_AFTER [FONTS_AFTER ...]
                        [--user-wordlist USER_WORDLIST] [--no-diffenator]
                        [--threshold THRESHOLD]

  --out OUT, -o OUT     Output dir
  --imgs                Generate images
  --filter-styles FILTER_STYLES
  --pt-size PT_SIZE, -pt PT_SIZE
  --styles {instances,cross_product,masters}, -s {instances,cross_product,masters}
                        Show font instances, cross product or master styles
  --fonts-before FONTS_BEFORE [FONTS_BEFORE ...], -fb FONTS_BEFORE [FONTS_BEFORE ...]
  --fonts-after FONTS_AFTER [FONTS_AFTER ...], -fa FONTS_AFTER [FONTS_AFTER ...]
  --user-wordlist USER_WORDLIST
  --no-diffenator
  --threshold THRESHOLD, -t THRESHOLD
```

#### Standard use: compare two families

The most typical usage is to compare two font families:

  ```
  # -fb == --fonts-before, -fa == --fonts-after
  diffenator2 diff -fb font1.ttf -fa font2.ttf -o out_dir
  ```

#### User Wordlist

Compare two font families and include a custom wordlist

  `diffenator2 diff -fb font1.ttf -fa font2.ttf --user-wordlist wordlist.txt -o out_dir`

A wordlist could be

- A csv file with the following columns:

  `string, script, lang, ot features...`

  script, lang and ot features are optional. An arbitrary number of ot features can be included e.g

  ```
  a,latn,dflt,ss01
  1/4,,,frac
  10/23,,,frac
  0123456789,,,numr,tnum
  ```

#### Filter Styles

The `--filter-styles` option can be used to select which styles should be compared

For example, to only diff regular and bold styles:

  `diffenator2 diff -fb font1.ttf -fa font2.ttf --filter-styles "Regular|Bold"`

- `--filter-styles` also accepts wildcards. To diff all Bold styles:

  `diffenator2 diff -fb font1.ttf -fa font2.ttf --filter-styles "Bold*"`

#### Choose locations 

`-s` is used to choose which locations of a variable font should be compared

- The default is to compare named instances. To only compare masters:

  `diffenator2 diff -fb font1.ttf -fa font2.ttf -s masters`

- To compare the cross product of min/default/max for each axis:

  `diffenator2 diff -fb font1.ttf -fa font2.ttf -s cross_product`

#### Choose specific characters 

`-ch` is used to select which characters to compare

To compare only ascii characters:

  `diffenator2 diff -fb font2.ttf -fa font2.ttf -ch "[!-~]"`

### `proof`

```
usage: diffenator2 proof [-h] [--out OUT] [--imgs]
                         [--filter-styles FILTER_STYLES] [--pt-size PT_SIZE]
                         [--styles {instances,cross_product,masters}]
                         fonts [fonts ...]
```

* Generate proofing docs for a family

`diffenator2 proof font1.ttf font2.ttf font3.ttf -o out_dir`

* Proof and include browser images

`diffenator2 proof font1.ttf font2.ttf font3.ttf -o out_dir --imgs`

* `--filter-styles` and `--styles` operate as above
