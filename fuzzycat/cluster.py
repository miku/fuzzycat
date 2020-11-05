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
from typing import List, Optional

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

# Notes: untie from release_entity, as we are only using a few fields. Maybe
# it's a jsob blob, with a pydantic spec and schema.


def release_key_title(doc: KeyDoc, get_ident_title=get_ident_title):
    id, title = get_ident_title(doc)
    if not title:
        raise ValueError('title missing')
    title = title.translate(ws_replacer).strip()
    return (id, title)


def release_key_title_normalized(doc: KeyDoc):
    id, title = release_key_title(doc)
    title = re.sub(r'[ ]{2,}', ' ', title)
    title = title.lower()
    return (id, non_word_re.sub('', title))


def release_key_title_nysiis(doc: KeyDoc):
    id, title = release_key_title(doc)
    return (id, fuzzy.nysiis(title))


def release_key_title_authors_ngram(doc: KeyDoc):
    """
    Derive a key from title and authors. Authors in contribs list:

      "contribs": [
	    {
	      "index": 0,
	      "raw_name": "Meise Botanic Garden",
	      "role": "author"
	    }
	],


    """
    # SS: compare ngram sets?


def sort_by_column(filename, opts="-k 2", fast=True, mode="w", prefix="fuzzycat-", tmpdir=None):
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


def group_by(seq, key=None, value=None, comment=""):
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


def cut(f=0, sep='\t', ignore_missing_column=True):
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
        counter = collections.Counter()
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
