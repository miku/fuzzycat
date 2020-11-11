# pylint: disable=C0103
"""
Clustering stage.

* [ ] verify needs whole document
* [ ] parallelization misses groups
* [ ] cached match key store (sqlite3), something ~/.cache/...
* [ ] reproducibly run test
* [ ] place for put md record tests

----

* [ ] hadoop -> py (bn)
* [ ] gnu parallel, share command line -- note (bn)

----

Ideas:

* lookup potential matches; TSV [key, ...]; sort
* maybe new "schema" - size vs "common schema" -- key <TAB> {"bibjson": ...}
* merge-join

```
$ fuzzycat.main keygen -s "algo" < ours | sort -k1,1 > a.tsv
$ fuzzycat.main keygen -s "algo" < other | sort -k1,1 > b.tsv
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
import operator
import os
import re
import string
import subprocess
import sys
import tempfile
import unicodedata
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import fuzzy
import regex
from pydantic import BaseModel

__all__ = [
    "release_key_title",
    "release_key_title_normalized",
    "release_key_title_nysiis",
    "release_key_title_sandcrawler",
    "sort_by_column",
    "group_by",
    "Cluster",
]


class Contrib(BaseModel):
    """
    A contributor.
    """
    index: Optional[int]
    raw_name: Optional[str]
    given_name: Optional[str]
    surname: Optional[str]
    role: Optional[str]


class KeyDoc(BaseModel):
    """
    A document from which we can derive a key, e.g. a release entity.
    """
    ident: str
    title: Optional[str]
    contribs: Optional[List[Contrib]]


class ClusterResult(BaseModel):
    """
    Result of clustering.

    XXX: We could also include the complete document, that would keep it simple
    at the expense of a few more things to read.
    """
    key: str
    values: List[str]
    comment: str
    ids: str
    title: str
    contribs: str
    year: str


get_ident_title = operator.itemgetter("ident", "title")
ws_replacer = str.maketrans({"\t": " ", "\n": " "})
non_word_re = re.compile(r'[\W_]+', re.UNICODE)
printable_no_punct = string.digits + string.ascii_letters + string.whitespace


def slugify_string(s: str) -> str:
    """
    Keeps ascii chars and single whitespace only.
    """
    return ''.join((c for c in s.lower() if c in printable_no_punct))


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
    'μ': 'u',
    '\N{LATIN LETTER INVERTED GLOTTAL STOP}': '',
}

SANDCRAWLER_PREFIX_REMOVE = [
    "original article: ",
    "original article ",
    "article: ",
    "title: ",
]

# regex that matches all characters which should be removed
SANDCRAWLER_REMOVE_CHAR_REGEX = regex.compile(
    r"[\s\p{Punct}\p{M}\p{InCombiningDiacriticalMarks}’·“”‘’“”«»「」¿–±§_`°ʖ©®¤]")


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
    slug = ''.join([(c in SANDCRAWLER_CHAR_MAP and SANDCRAWLER_CHAR_MAP[c]) or c for c in slug])

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
        ("μmeter", "umeter"),
        # TODO: ("salt &and; pepper", "saltpepper"),
        # TODO: ("new <b>and</b> improved", "newandimproved"),

        # some via https://github.com/minimaxir/big-list-of-naughty-strings/blob/master/blns.txt
        ("¡™£¢∞§¶•ªº–≠ ", "tm£¢∞ao="),
        ("⁰⁴⁵₀₁₂", "045012"),
        ("社會科學院語學研究所", "社會科學院語學研究所"),
        # TODO: ("パーティーへ行かないか", "パーティーへ行かないか"),
        # TODO: ("表ポあA鷗ŒéＢ逍Üßªąñ丂㐀𠀀", "表ポあa鷗oeebＢ逍usaan丂㐀𠀀"),
        ("( ͡° ͜ʖ ͡°)", ""),
        # emoji ok? I guess
        ("👾 🙇 💁 🙅 🙆 🙋 🙎 🙍", "👾🙇💁🙅🙆🙋🙎🙍"),
        ("2️⃣ 3️⃣ 4️⃣ 5️⃣", "2345"),
        ("﷽ ", "﷽"),
        ("̗̺͖̹̯͓Ṯ̤͍̥͇͈h̲́e͏͓̼̗̙̼̣͔ ͇̜̱̠͓͍ͅN͕͠e̗̱z̘̝̜̺͙p̤̺̹͍̯͚e̠̻̠͜r̨̤͍̺̖͔̖̖d̠̟̭̬̝͟i̦͖̩͓͔̤a̠̗̬͉̙n͚͜ ̻̞̰͚ͅh̵͉i̳̞v̢͇ḙ͎͟-҉̭̩̼͔m̤̭̫i͕͇̝̦n̗͙ḍ̟ ̯̲͕͞ǫ̟̯̰̲͙̻̝f ̪̰̰̗̖̭̘͘c̦͍̲̞͍̩̙ḥ͚a̮͎̟̙͜ơ̩̹͎s̤.̝̝ ҉Z̡̖̜͖̰̣͉̜a͖̰͙̬͡l̲̫̳͍̩g̡̟̼̱͚̞̬ͅo̗͜.̟",
         "thenezperdianhivemindofchaoszalgo"),
        ("Ｔｈｅ ｑｕｉｃｋ ｂｒｏｗｎ ｆｏｘ ｊｕｍｐｓ ｏｖｅｒ ｔｈｅ ｌａｚｙ ｄｏｇ", "thequickbrownfoxjumpsoverthelazydog"),
        ("Ｔｈｅ ｑｕｉｃｋ ｂｒｏｗｎ ｆｏｘ ｊｕｍｐｓ ｏｖｅｒ ｔｈｅ ｌａｚｙ ｄｏｇ", "thequickbrownfoxjumpsoverthelazydog"),
        ("𝕋𝕙𝕖 𝕢𝕦𝕚𝕔𝕜 𝕓𝕣𝕠𝕨𝕟 𝕗𝕠𝕩 𝕛𝕦𝕞𝕡𝕤 𝕠𝕧𝕖𝕣 𝕥𝕙𝕖 𝕝𝕒𝕫𝕪 𝕕𝕠𝕘 ", "thequickbrownfoxjumpsoverthelazydog"),
    ]

    for in_str, out_str in test_cases:
        if sandcrawler_slugify(in_str) != out_str:
            for c in list(sandcrawler_slugify(in_str)):
                print(unicodedata.name(c))
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
    Derive a key from title and authors. Authors in contribs list:

    "contribs": [
        {
            "index": 0,
            "raw_name": "Meise Botanic Garden",
            "role": "author"
        }
    ],

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


def sort_by_column(filename: str,
                   opts: str = "-k 2",
                   fast: bool = True,
                   mode: str = "w",
                   prefix: str = "fuzzycat-",
                   tmpdir: Optional[str] = None):
    """
    Sort tabular file with sort(1), returns the filename of the sorted file.
    TODO: use separate /fast/tmp for sort.
    """
    with tempfile.NamedTemporaryFile(delete=False, mode=mode, prefix=prefix) as tf:
        env = os.environ.copy()
        if tmpdir is not None:
            env["TMPDIR"] = tmpdir
        if fast:
            env["LC_ALL"] = "C"
        subprocess.run(["sort"] + opts.split() + [filename], stdout=tf, env=env, check=True)

    return tf.name


def group_by(seq: collections.abc.Iterable,
             key: Callable[[Any], str] = None,
             value: Callable[[Any], str] = None,
             comment: str = "") -> Generator[Any, None, None]:
    """
    Iterate over lines in filename, group by key (a callable deriving the key
    from the line), then apply value callable on the same value to emit a
    minimal document, containing the key and identifiers belonging to a
    cluster.
    """
    for k, g in itertools.groupby(seq, key=key):
        doc = {
            "k": k.strip(),
            "v": [value(v) for v in g],
        }
        if comment:
            doc["c"] = comment
        yield doc


def cut(f: int = 0, sep: str = '\t', ignore_missing_column: bool = True):
    """
    Return a callable, that extracts a given column from a file with a specific
    separator. TODO: move this into more generic place.
    """
    def func(value):
        parts = value.strip().split(sep)
        if f >= len(parts):
            if ignore_missing_column:
                return ""
            raise ValueError('cannot split value {} into {} parts'.format(value, f))
        return parts[f]

    return func


class Cluster:
    """
    Cluster scaffold for release entities. XXX: move IO/files out, allow any iterable.
    """
    def __init__(self,
                 files="-",
                 output=sys.stdout,
                 keyfunc=lambda v: v,
                 prefix='fuzzycat-',
                 key_denylist=None,
                 tmpdir=None):
        """
        Files can be a list of files or "-" for stdin.
        """
        self.files = files
        self.keyfunc = keyfunc
        self.output = output
        self.prefix = prefix
        self.tmpdir = tmpdir
        self.logger = logging.getLogger('fuzzycat.cluster')
        self.key_denylist = key_denylist

    def run(self):
        """
        Run clustering and write output to given stream or file.
        """
        keyfunc = self.keyfunc  # Save a lookup in loop.
        counter: Dict[str, int] = collections.Counter()
        with tempfile.NamedTemporaryFile(delete=False, mode="w", prefix=self.prefix) as tf:
            for line in fileinput.input(files=self.files):
                try:
                    ident, key = keyfunc(json.loads(line))
                except (KeyError, ValueError):
                    counter["key_extraction_failed"] += 1
                    continue
                if not key:
                    counter["key_empty"] += 1
                    continue
                if self.key_denylist and key in self.key_denylist:
                    counter["key_denylist"] += 1
                    continue
                counter["key_ok"] += 1
                print("{}\t{}".format(ident, key), file=tf)
        sbc = sort_by_column(tf.name, opts='-k 2', prefix=self.prefix, tmpdir=self.tmpdir)
        with open(sbc) as f:
            comment = keyfunc.__name__
            for doc in group_by(f, key=cut(f=1), value=cut(f=0), comment=comment):
                counter["groups"] += 1
                json.dump(doc, self.output)
                self.output.write("\n")

        os.remove(sbc)
        os.remove(tf.name)

        return counter
