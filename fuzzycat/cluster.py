# pylint: disable=C0103
"""
Clustering stage.
"""

import collections
import fileinput
import itertools
import json
import logging
import operator
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import fuzzy
from pydantic import BaseModel

__all__ = [
    "release_key_title",
    "release_key_title_normalized",
    "release_key_title_nysiis",
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


get_ident_title = operator.itemgetter("ident", "title")
ws_replacer = str.maketrans({"\t": " ", "\n": " "})
non_word_re = re.compile(r'[\W_]+', re.UNICODE)
printable_no_punct = string.digits + string.letters + string.whitespace

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
    slug_title = slug_title(title)
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

    def run(self):
        """
        Run clustering and write output to given stream or file.
        """
        keyfunc = self.keyfunc  # Save a lookup in loop.
        counter: Dict[str, int] = collections.Counter()
        with tempfile.NamedTemporaryFile(delete=False, mode="w", prefix=self.prefix) as tf:
            for line in fileinput.input(files=self.files):
                try:
                    id, key = keyfunc(json.loads(line))
                    print("{}\t{}".format(id, key), file=tf)
                except (KeyError, ValueError):
                    counter["key_extraction_failed"] += 1
                else:
                    counter["key_ok"] += 1
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
