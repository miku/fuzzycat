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

import fuzzy

__all__ = [
    "release_key_title",
    "release_key_title_normalized",
    "release_key_title_nysiis",
    "sort_by_column",
    "group_by",
    "Cluster",
]

get_ident_title = operator.itemgetter("ident", "title")
ws_replacer = str.maketrans({"\t": " ", "\n": " "})
non_word_re = re.compile(r'[\W_]+', re.UNICODE)


def release_key_title(release_entity, get_ident_title=get_ident_title):
    id, title = get_ident_title(release_entity)
    if not title:
        raise ValueError('title missing')
    title = title.translate(ws_replacer).strip()
    return (id, title)


def release_key_title_normalized(release_entity):
    id, title = release_key_title(release_entity)
    title = re.sub(r'[ ]{2,}', ' ', title)
    title = title.lower()
    return (id, non_word_re.sub('', title))


def release_key_title_nysiis(release_entity):
    id, title = release_key_title(release_entity)
    return (id, fuzzy.nysiis(title))


def release_key_title_authors_ngram(release_entity):
    """
    Derive a key from title and authors.
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
    from the line), then apply value callable to emit a minimal document.
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
    Cluster scaffold for release entities.
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
                except (KeyError, ValueError) as exc:
                    counter["key_extraction_failed"] += 1
                    continue
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
