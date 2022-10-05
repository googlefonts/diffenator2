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
import sys
import os
from collections import namedtuple
from pkg_resources import resource_filename
from PIL import Image
from configparser import ConfigParser
from gflanguages import LoadLanguages
from functools import lru_cache
import requests
import sys
import os
from zipfile import ZipFile
import tempfile
from io import BytesIO



def google_fonts_has_family(name):
    url_name = name.replace(" ", "+")
    url = f"https://fonts.google.com/specimen/{url_name}"
    r = requests.get(url)
    return True if r.status_code == 200 else False


def download_file(url, dst_path=None):
    """Download a file from a url. If no dst_path is specified, store the file
    as a BytesIO object"""
    request = requests.get(url, stream=True)
    if not dst_path:
        return BytesIO(request.content)
    with open(dst_path, 'wb') as downloaded_file:
        downloaded_file.write(request.content)


def download_latest_github_release_archive(user, repo, out=None, gh_token="GH_TOKEN"):
    headers = {"Authorization": f"Bearer {os.environ[gh_token]}"}
    latest_release = requests.get(
        f"https://api.github.com/repos/{user}/{repo}/releases/latest",
        headers=headers,
    ).json()
    assets = latest_release["assets"]
    dl_url = assets[0]["browser_download_url"]
    zip_file = download_file(dl_url, out)
    zip_dir = zip_file.replace(".zip", "")
    z = ZipFile(zip_file)
    z.extractall(zip_dir)
    return zip_dir


def download_google_fonts_family(name, dst=None, ignore_static=True):
    """Download a font family from Google Fonts"""
    if not google_fonts_has_family(name):
        raise ValueError(f"No family on Google Fonts named {name}")

    url = 'https://fonts.google.com/download?family={}'.format(
        name.replace(' ', '%20')
    )
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


def gen_gifs(dir1, dir2, dst_dir):
    dir1_imgs = set(f for f in os.listdir(dir1) if f.endswith(("jpg", "png")))
    dir2_imgs = set(f for f in os.listdir(dir2) if f.endswith(("jpg", "png")))
    shared_imgs = dir1_imgs & dir2_imgs
    for img in shared_imgs:
        gif_filename = img[:-4] + ".gif"
        img_a_path = os.path.join(dir1, img)
        img_b_path = os.path.join(dir2, img)
        dst = os.path.join(dst_dir, gif_filename)
        gen_gif(img_a_path, img_b_path, dst)


def gen_gif(img_a_path, img_b_path, dst):
    with Image.open(img_a_path) as img_a, Image.open(img_b_path) as img_b:
        img_a.save(dst, save_all=True, append_images=[img_b], loop=10000, duration=1000)


def partition(items, size):
    """partition([1,2,3,4,5,6], 2) --> [[1,2],[3,4],[5,6]]"""
    return [items[i : i + size] for i in range(0, len(items), size)]


@lru_cache()
def font_sample_text(ttFont):
    """Collect words which exist in the Universal Declaration of Human Rights
    that can be formed using the ttFont instance.
    UDHR has been chosen due to the many languages it covers"""
    with open(resource_filename("diffenator", "data/udhr_all.txt")) as doc:
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
                for key, text in proto.sample_text.ListFields():
                    _add_words(words, text, seen_chars)

    return words
