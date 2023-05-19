#!/usr/bin/env python3
# Copyright 2016 The Fontbakery Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import annotations
import os
from pkg_resources import resource_filename
from PIL import Image
from gflanguages import LoadLanguages
from functools import lru_cache
import requests
from urllib.request import urlretrieve
import os
from io import BytesIO
from fontTools.ttLib import TTFont
from zipfile import ZipFile
import re


def dict_coords_to_string(coords: dict[str, float]) -> str:
    return ",".join(f"{k}={v}" for k, v in coords.items())


def string_coords_to_dict(string: str) -> dict[str, float]:
    if not string:
        return {}
    return {s.split("=")[0]: float(s.split("=")[1]) for s in string.split(",")}


def google_fonts_has_family(name: str) -> bool:
    url_name = name.replace(" ", "+")
    url = f"https://fonts.google.com/specimen/{url_name}"
    r = requests.get(url)
    return True if r.status_code == 200 else False


def download_file(url: str, dst_path: str = "", headers: dict[str, str] = {}):
    """Download a file from a url. If no dst_path is specified, store the file
    as a BytesIO object"""
    if not dst_path:
        request = requests.get(url, stream=True, headers=headers)
        return BytesIO(request.content)
    urlretrieve(url, dst_path)


def download_latest_github_release(
    user: str,
    repo: str,
    dst: str = None,
    github_token: str = None,
    ignore_static: bool = True,
):
    headers = {}
    if github_token:
        headers["Authorization"] = f"Token {github_token}"
    latest_release = requests.get(
        f"https://api.github.com/repos/{user}/{repo}/releases/latest",
        headers=headers,
    ).json()
    headers["Accept"] = "application/octet-stream"
    dl_url = latest_release["assets"][0]["url"]
    zip_file = download_file(dl_url, headers=headers)
    z = ZipFile(zip_file)
    files = []
    for filename in z.namelist():
        if ignore_static and "static" in filename:
            continue
        if dst:
            target = os.path.join(dst, filename)
            z.extract(filename, dst)
            files.append(target)
        else:
            files.append(BytesIO(z.read(filename)))
    return files


def download_google_fonts_family(
    name: str, dst: str = None, ignore_static: bool = True
):
    """Download a font family from Google Fonts"""
    if not google_fonts_has_family(name):
        raise ValueError(f"No family on Google Fonts named {name}")

    url = "https://fonts.google.com/download?family={}".format(name.replace(" ", "%20"))
    dl = download_file(url)
    zipfile = ZipFile(dl)
    fonts = []
    for filename in zipfile.namelist():
        if ignore_static and "static" in filename:
            continue
        if filename.endswith(".ttf"):
            if dst:
                target = os.path.join(dst, filename)
                zipfile.extract(filename, dst)
                fonts.append(target)
            else:
                fonts.append(BytesIO(zipfile.read(filename)))
    return fonts


# our images can be huge so disable this
Image.MAX_IMAGE_PIXELS = None


def gen_gifs(dir1: str, dir2: str, dst_dir: str):
    dir1_imgs = set(f for f in os.listdir(dir1) if f.endswith(("jpg", "png")))
    dir2_imgs = set(f for f in os.listdir(dir2) if f.endswith(("jpg", "png")))
    shared_imgs = dir1_imgs & dir2_imgs
    for img in shared_imgs:
        # We use apng format since a gif's dimensions are limited to 64kx64k
        # we have encountered many diffs which are taller than this.
        gif_filename = img[:-4] + ".gif"
        img_a_path = os.path.join(dir1, img)
        img_b_path = os.path.join(dir2, img)
        dst = os.path.join(dst_dir, gif_filename)
        gen_gif(img_a_path, img_b_path, dst)


def gen_gif(img_a_path: str, img_b_path: str, dst: str):
    with Image.open(img_a_path) as img_a, Image.open(img_b_path) as img_b:
        img_a.save(dst, save_all=True, append_images=[img_b], loop=10000, duration=1000)


@lru_cache()
def font_sample_text(ttFont: TTFont) -> str:
    """Collect words which exist in the Universal Declaration of Human Rights
    that can be formed using the ttFont instance.
    UDHR has been chosen due to the many languages it covers"""
    with open(
        resource_filename("diffenator2", "data/udhr_all.txt"), encoding="utf8"
    ) as doc:
        uhdr = doc.read()

    cmap = set(ttFont.getBestCmap())
    words = []
    seen_chars = set()

    def _add_words(words, text, seen_chars):
        for word in text.split():
            chars = set(ord(l) for l in word)
            if not chars.issubset(cmap):
                continue
            if chars & seen_chars == chars:
                continue
            seen_chars |= chars
            words.append(word)

    _add_words(words, uhdr, seen_chars)

    if len(seen_chars) < len(cmap):
        languages = LoadLanguages()
        for file, proto in languages.items():
            if hasattr(proto, "sample_text"):
                for _, text in proto.sample_text.ListFields():
                    _add_words(words, text, seen_chars)
    return words


def font_family_name(ttFont, suffix=""):
    familyname = ttFont["name"].getBestFamilyName()
    if suffix:
        return f"{suffix} {familyname}"
    else:
        return familyname


def partition(items, size):
    """partition([1,2,3,4,5,6], 2) --> [[1,2],[3,4],[5,6]]"""
    return [items[i : i + size] for i in range(0, len(items), size)]


def re_filter_characters(font, pattern):
    characters_in_font = set(chr(g) for g in font.ttFont.getBestCmap())
    return set(g for g in characters_in_font if re.search(pattern, g))


def characters_in_string(string, characters):
    return all(g in characters for g in string)
