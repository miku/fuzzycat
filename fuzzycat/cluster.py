# pylint: disable=C0103
"""
Clustering stage.

* [x] verify needs whole document
* [ ] parallelization misses groups
* [ ] cached match key store (tsv, sqlite3), something ~/.cache/...
* [x] reproducibly run tests
* [x] place for put md/tsv record tests

----

* [x] hadoop -> py (bn)
* [ ] gnu parallel, share command line -- note (bn)

----

Ideas:

* lookup potential matches; TSV [key, ...]; sort
* maybe new "schema" - size vs "common schema" -- key <TAB> {"bibjson": ...}
* merge-join

```
$ python -m fuzzycat keygen -s "algo" < ours | sort -k1,1 > a.tsv
$ python -m fuzzycat keygen -s "algo" < other | sort -k1,1 > b.tsv
$ merge-join a.tsv b.tsv
```

A couple of "keygen" algos.

> 10k/s, 1B, ~day

Partial fields should be ok.

Q:

* nysiis

Deps.

* pydantic; json "omitempty" -- get rid of it?
* orjson (serialize datetime) -- maybe enough w/ dataclasses w/ dataclasses

fuzzycat.main -> `__main__.py`

* elasticsearch-py >> elasticsearch

Matching releases to non-release entities.

----

Features and integration.

* work grouping at import time; random pdfs; requires strong verification (vs cgraph)
* email out to OCI

"""

import collections
import fileinput
import itertools
import json
import logging
import multiprocessing
import operator
import os
import re
import string
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from typing import IO, Any, Callable, Dict, Generator, List, Optional, Tuple

import fuzzy
import regex
import zstandard

from fuzzycat.utils import cut, shellout, slugify_string, zstdlines

__all__ = [
    "release_key_title",
    "release_key_title_normalized",
    "release_key_title_nysiis",
    "release_key_title_sandcrawler",
    "Cluster",
]


@dataclass
class KeyDoc:
    """
    A document from which we can derive a key, e.g. a release entity.
    """
    ident: str
    title: str


get_ident_title = operator.itemgetter("ident", "title")
ws_replacer = str.maketrans({"\t": " ", "\n": " "})
non_word_re = re.compile(r'[\W_]+', re.UNICODE)

# Notes: untie from release_entity, as we are only using a few fields. Maybe
# it's a jsob blob, with a pydantic spec and schema.


def release_key_title(doc: KeyDoc) -> Tuple[str, str]:
    ident, title = get_ident_title(doc)
    if not title:
        raise ValueError('title missing for {}'.format(ident))
    title = title.translate(ws_replacer).strip()
    return (ident, title)


def release_key_title_normalized(doc: KeyDoc) -> Tuple[str, str]:
    ident, title = release_key_title(doc)
    title = re.sub(r'[ ]{2,}', ' ', title).lower()
    return (ident, non_word_re.sub('', title))


def release_key_title_nysiis(doc: KeyDoc) -> Tuple[str, str]:
    """
    Use NYSIIS New York State Identification and Intelligence System.
    """
    ident, title = release_key_title(doc)
    return (ident, fuzzy.nysiis(title))


# from http://zderadicka.eu/removing-diacritics-marks-from-strings/
SANDCRAWLER_CHAR_MAP = {
    '\N{Latin capital letter AE}': 'AE',
    '\N{Latin small letter ae}': 'ae',
    '\N{Latin capital letter Eth}': 'D',
    '\N{Latin small letter eth}': 'd',
    '\N{Latin capital letter O with stroke}': 'O',
    '\N{Latin small letter o with stroke}': 'o',
    '\N{Latin capital letter Thorn}': 'Th',
    '\N{Latin small letter thorn}': 'th',
    '\N{Latin small letter sharp s}': 's',
    '\N{Latin capital letter D with stroke}': 'D',
    '\N{Latin small letter d with stroke}': 'd',
    '\N{Latin capital letter H with stroke}': 'H',
    '\N{Latin small letter h with stroke}': 'h',
    '\N{Latin small letter dotless i}': 'i',
    '\N{Latin small letter kra}': 'k',
    '\N{Latin capital letter L with stroke}': 'L',
    '\N{Latin small letter l with stroke}': 'l',
    '\N{Latin capital letter Eng}': 'N',
    '\N{Latin small letter eng}': 'n',
    '\N{Latin capital ligature OE}': 'Oe',
    '\N{Latin small ligature oe}': 'oe',
    '\N{Latin capital letter T with stroke}': 'T',
    '\N{Latin small letter t with stroke}': 't',

    # bnewbold additions
    '\N{MICRO SIGN}': 'u',
    '\N{LATIN SMALL LETTER C}': 'c',
    '\N{LATIN SMALL LETTER F WITH HOOK}': 'f',
    # bnewbold map-to-null (for non-printing stuff not in the regex)
    '\N{PARTIAL DIFFERENTIAL}': '',
    '\N{LATIN LETTER INVERTED GLOTTAL STOP}': '',
    '\N{N-ARY SUMMATION}': '',
    '\N{N-ARY PRODUCT}': '',
    '\N{MODIFIER LETTER CIRCUMFLEX ACCENT}': '',
    '\N{SNOWMAN}': '',
    '\N{CARON}': '',
}

SANDCRAWLER_PREFIX_REMOVE = [
    "original article: ",
    "original article ",
    "article: ",
    "title: ",
]

# regex that matches all characters which should be removed
SANDCRAWLER_REMOVE_CHAR_REGEX = regex.compile(
    r"[\s\p{Punctuation}\p{M}\p{InCombiningDiacriticalMarks}\u2000-\u206F\u2E00-\u2E7F’·“”‘’“”«»「」¿–±§_`°ʖ©®¤=<>|+$^~≈√∫≤≥÷ƒ∆¬£¢∞¥◊€]"
)


def sandcrawler_slugify(raw: str) -> str:
    """
    Python re-implementation of sandcrawler Scala code for string comparison
    ("scorable" strings)
    """
    slug = raw.strip().lower()

    # transforms before running regex
    for prefix in SANDCRAWLER_PREFIX_REMOVE:
        if slug.startswith(prefix):
            slug = slug[:len(prefix)]

    slug = slug.replace("&apos;", "'")

    # iterate over all chars and replace from map, if in map; then lower-case again
    slug = ''.join([SANDCRAWLER_CHAR_MAP.get(c, c) for c in slug])

    # early bailout before executing regex
    if not slug:
        return ""

    slug = unicodedata.normalize('NFKD', slug)
    slug = SANDCRAWLER_REMOVE_CHAR_REGEX.sub('', slug)

    return slug.lower()


def test_sandcrawler_slugify() -> None:
    test_cases = [
        ("", ""),
        ("asdf", "asdf"),
        ("'Hello World!'", "helloworld"),
        ("ASDF", "asdf"),
        ("as\n  df", "asdf"),
        ("as\u0142  bb \u00f8", "aslbbo"),
        ("`hello¿", "hello"),
        ("علمية", "علمية"),
        ("期刊的数字", "期刊的数字"),
        ("les pré-impressions explorées à partir", "lespreimpressionsexploreesapartir"),

        # "MICRO SIGN"
        ("\xb5meter", "umeter"),
        # "GREEK SMALL LETTER MU"
        ("\u03bcmeter", "\u03bcmeter"),

        # TODO: ("salt &and; pepper", "saltpepper"),
        # TODO: ("new <b>and</b> improved", "newandimproved"),

        # some via https://github.com/minimaxir/big-list-of-naughty-strings/blob/master/blns.txt
        ("-9223372036854775808/-1", "92233720368547758081"),
        (r",./;'[]\-= <>?:\"{}|_+ !@#$%^&*()`~", ""),
        (" \n\r \x85 \u1680\u2002\u2003\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u202f\u205f\u3000",
         ""),
        (r"Ω≈ç√∫˜≤≥÷", "ωc"),
        (r"åß∂ƒ©˙∆˚¬…æ", "asfae"),
        (r"œ∑´®†¥¨ˆøπ“‘", "oeoπ"),
        (r"¡™£¢∞§¶•ªº–≠ ", "tmao"),
        (r"¸˛Ç◊ı˜Â¯˘¿", "cia"),
        (r"ÅÍÎÏ˝ÓÔÒÚÆ☃", "aiiiooouae"),
        (r"Œ„´‰ˇÁ¨ˆØ∏”’", "oeao"),
        (r"`⁄€‹›ﬁﬂ‡°·‚—±", "fifl"),
        (r"ЁЂЃЄЅІЇЈЉЊЋЌЍЎЏАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюя",
         "еђгєѕііјљњћкиуџабвгдежзииклмнопрстуфхцчшщъыьэюяабвгдежзииклмнопрстуфхцчшщъыьэюя"),
        (r"⁰⁴⁵₀₁₂", "045012"),
        (r"社會科學院語學研究所", "社會科學院語學研究所"),
        # TODO: ("パーティーへ行かないか", "パーティーへ行かないか"),
        # TODO: ("表ポあA鷗ŒéＢ逍Üßªąñ丂㐀𠀀", "表ポあa鷗oeebＢ逍usaan丂㐀𠀀"),
        (r"( ͡° ͜ʖ ͡°)", ""),
        # emoji ok? I guess
        (r"👾 🙇 💁 🙅 🙆 🙋 🙎 🙍", "👾🙇💁🙅🙆🙋🙎🙍"),
        (r"2️⃣ 3️⃣ 4️⃣ 5️⃣", "2345"),
        (r"﷽ ", "﷽"),
        (r"\"̗̺͖̹̯͓Ṯ̤͍̥͇͈h̲́e͏͓̼̗̙̼̣͔ ͇̜̱̠͓͍ͅN͕͠e̗̱z̘̝̜̺͙p̤̺̹͍̯͚e̠̻̠͜r̨̤͍̺̖͔̖̖d̠̟̭̬̝͟i̦͖̩͓͔̤a̠̗̬͉̙n͚͜ ̻̞̰͚ͅh̵͉i̳̞v̢͇ḙ͎͟-҉̭̩̼͔m̤̭̫i͕͇̝̦n̗͙ḍ̟ ̯̲͕͞ǫ̟̯̰̲͙̻̝f ̪̰̰̗̖̭̘͘c̦͍̲̞͍̩̙ḥ͚a̮͎̟̙͜ơ̩̹͎s̤.̝̝ ҉Z̡̖̜͖̰̣͉̜a͖̰͙̬͡l̲̫̳͍̩g̡̟̼̱͚̞̬ͅo̗͜.̟",
         "thenezperdianhivemindofchaoszalgo"),
        (r"Ｔｈｅ ｑｕｉｃｋ ｂｒｏｗｎ ｆｏｘ ｊｕｍｐｓ ｏｖｅｒ ｔｈｅ ｌａｚｙ ｄｏｇ", "thequickbrownfoxjumpsoverthelazydog"),
        (r"Ｔｈｅ ｑｕｉｃｋ ｂｒｏｗｎ ｆｏｘ ｊｕｍｐｓ ｏｖｅｒ ｔｈｅ ｌａｚｙ ｄｏｇ", "thequickbrownfoxjumpsoverthelazydog"),
        (r"𝕋𝕙𝕖 𝕢𝕦𝕚𝕔𝕜 𝕓𝕣𝕠𝕨𝕟 𝕗𝕠𝕩 𝕛𝕦𝕞𝕡𝕤 𝕠𝕧𝕖𝕣 𝕥𝕙𝕖 𝕝𝕒𝕫𝕪 𝕕𝕠𝕘 ", "thequickbrownfoxjumpsoverthelazydog"),
    ]

    for in_str, out_str in test_cases:
        if sandcrawler_slugify(in_str) != out_str:
            for c in list(sandcrawler_slugify(in_str)):
                try:
                    print(unicodedata.name(c))
                except ValueError:
                    print(ord(c))
                #print(ord(c))
            print("----")
            for c in list(out_str):
                print(unicodedata.name(c))
            print(in_str)
        assert sandcrawler_slugify(in_str) == out_str


def release_key_title_sandcrawler(doc: KeyDoc) -> Tuple[str, str]:
    ident, title = release_key_title(doc)
    slug = sandcrawler_slugify(title)
    return (ident, slug)


def release_key_title_ngram(doc: KeyDoc, n=3) -> Tuple[str, str]:
    """
    Derive a key from title.

    Tokenize title, remote stopwords, lookup first three, lookup last three,
    plus authors. TODO(miku): authors.
    """
    ident, title = get_ident_title(doc)
    slug_title = slugify_string(title)
    tokens = slug_title.split()
    if len(tokens) < 2 * n:
        key = ''.join(tokens)
    else:
        key = ''.join(tokens[:3] + tokens[-3:])
    return (ident, key)


class Cluster:
    """
    Setup and run clustering over a potentially large (100m) number of records.

    Two main options are iterable (TODO: work on parsed docs), and the key
    function to apply to value to group by.

    TODO: We want compression.
    """
    def __init__(self,
                 iterable: collections.abc.Iterable,
                 key: Callable[[Any], Tuple[str, str]],
                 output: IO[str] = sys.stdout,
                 key_denylist: Optional[List[str]] = None,
                 prefix: str = "fuzzycat-",
                 tmpdir: str = tempfile.gettempdir(),
                 strict: bool = False,
                 min_cluster_size: int = 2,
                 max_cluster_size: int = 100,
                 compress=False,
                 verbose=True):
        self.iterable: collections.abc.Iterable = iterable
        self.key: Callable[[Any], Tuple[str, str]] = key
        self.output: IO[str] = output
        self.prefix: str = prefix
        self.tmpdir: str = tmpdir
        self.strict = strict
        self.key_denylist = key_denylist
        self.min_cluster_size = min_cluster_size
        self.max_cluster_size = max_cluster_size
        self.verbose = verbose
        self.compress = compress
        self.counter: Dict[str, int] = collections.Counter({
            "key_fail": 0,
            "key_ok": 0,
            "key_empty": 0,
            "key_denylist": 0,
            "num_clusters": 0,
        })

    def run(self):
        """
        First map documents to keys, then group by keys, outline: json -> tsv
        -> sort -> group -> json.
        """
        with tempfile.NamedTemporaryFile(delete=False, mode="wb", prefix=self.prefix) as tf:
            if self.compress:
                zc = zstandard.ZstdCompressor(level=9, threads=multiprocessing.cpu_count())
                writer = zc.stream_writer(tf)
            else:
                writer = tf
            for i, line in enumerate(self.iterable):
                if self.verbose and i % 100000 == 0:
                    print("@{}".format(i), file=sys.stderr)
                try:
                    doc = json.loads(line)
                    id, key = self.key(doc)
                except (KeyError, ValueError):
                    if self.strict:
                        raise
                    self.counter["key_fail"] += 1
                    continue
                if not key:
                    self.counter["key_empty"] += 1
                    continue
                if self.key_denylist and key in self.key_denylist:
                    self.counter["key_denylist"] += 1
                    continue
                self.counter["key_ok"] += 1
                # XXX: if the line itself contains tabs, we need to remove
                # them here; maybe offer TSV and JSON output and extra flag
                # XXX: this needs to be compressed (e.g. with 2B records, we
                # fill up disk too quickly)
                data = bytes("{}\t{}\t{}\n".format(id, key,
                                                   line.replace("\t", " ").strip()),
                             encoding="utf-8")
                writer.write(data)
            if self.compress:
                writer.flush(zstandard.FLUSH_FRAME)

        sf = self.sort(tf.name, opts='-k 2')
        if self.compress:
            f = zstdlines(sf)
        else:
            f = open(sf)

        for doc in self.group_by(f, key=cut(f=1)):
            if len(doc["v"]) < self.min_cluster_size:
                continue
            self.counter["num_clusters"] += 1
            json.dump(doc, self.output)
            self.output.write("\n")

        os.remove(sf)
        os.remove(tf.name)
        return self.counter

    def sort(self, filename: str, opts: str = "-k 2", fast: bool = True, mode: str = "w"):
        """
        Sort tabular file with sort(1), returns the filename of the sorted
        file. Options to sort can be passed in via opts keyword argument.
        """
        with tempfile.NamedTemporaryFile(delete=False, mode=mode, prefix=self.prefix) as tf:
            env = os.environ.copy()
            env["TMPDIR"] = self.tmpdir
            if fast:
                env["LC_ALL"] = "C"
            if self.compress:
                output = shellout(
                    "zstdcat -T0 {input} | LC_ALL=C TMPDIR={tmpdir} sort {opts} | zstd -T0 -c9 > {output}",
                    input=filename,
                    tmpdir=self.tmpdir,
                    opts=opts)
            else:
                subprocess.run(["sort"] + opts.split() + [filename], stdout=tf, env=env, check=True)
                output = tf.name

        return output

    def group_by(self,
                 seq: collections.abc.Iterable,
                 key: Callable[[Any], str] = None) -> Generator[Any, None, None]:
        """
        Extract a key from elements of an iterable and group them. Just as
        uniq(1), the input iterable must be ordered (by the key that is
        extracted) for this to work.

        There might be large clusters, which would currently exceed memory,
        hence the max_cluster_size option.
        """
        for k, g in itertools.groupby(seq, key=key):
            payload = []
            for i, line in enumerate(g):
                if i > 0 and i == self.max_cluster_size:
                    print('max cluster size cut off for: {}'.format(k), file=sys.stderr)
                    break
                # XXX: This is a bit too much "serde", get rid of this.
                fields = line.split("\t")
                if len(fields) < 3:
                    continue
                payload.append(json.loads(fields[2]))
            doc = {
                "k": k.strip(),
                "v": payload,
            }
            yield doc
