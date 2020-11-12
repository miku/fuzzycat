# pylint: disable=C0103
"""
Clustering stage.

* [ ] verify needs whole document
* [ ] parallelization misses groups
* [ ] cached match key store (tsv, sqlite3), something ~/.cache/...
* [ ] reproducibly run tests
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
from dataclasses import dataclass, field
from typing import IO, Any, Callable, Dict, Generator, List, Optional, Tuple

import fuzzy

__all__ = [
    "release_key_title",
    "release_key_title_normalized",
    "release_key_title_nysiis",
    "sort_by_column",
    "group_by",
    "Cluster",
]


@dataclass
class Contrib:
    """
    A contributor.
    """
    index: Optional[int]
    raw_name: Optional[str]
    given_name: Optional[str]
    surname: Optional[str]
    role: Optional[str]


@dataclass
class KeyDoc:
    """
    A document from which we can derive a key, e.g. a release entity.
    """
    ident: str
    title: str
    contribs: List[Contrib] = field(default_factory=list)


@dataclass
class ClusterResult:
    """
    Result of clustering, one key and a list of

    A first approach: pass document through.
    """
    key: str
    comment: str
    docs: List[Any] = field(default_factory=list)


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
    """
    Use NYSIIS New York State Identification and Intelligence System.
    """
    ident, title = release_key_title(doc)
    return (ident, fuzzy.nysiis(title))


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
    Runs clustering over a potentially large number of records.
    """
    def __init__(self,
                 iterable: collections.abc.Iterable,
                 key: Callable[[Any], Tuple[str, str]],
                 output: IO[str] = sys.stdout,
                 prefix: str = "fuzzycat-",
                 tmpdir: str = tempfile.gettempdir(),
                 strict: bool = False):
        """
        Setup a clusterer, using a custom key function.
        """
        self.iterable: collections.abc.Iterable = iterable
        self.key: Callable[[Any], Tuple[str, str]] = key
        self.output: IO[str] = output
        self.prefix: str = prefix
        self.tmpdir: str = tmpdir
        self.counter: Dict[str, int] = collections.Counter({
            "key_err": 0,
            "key_ok": 0,
            "num_clusters": 0,
        })

    def run(self):
        """
        First map documents to keys, then group by keys.

        Outline: json -> tsv -> sort -> group -> json
        """
        with tempfile.NamedTemporaryFile(delete=False, mode="w", prefix=self.prefix) as tf:
            for line in self.iterable:
                try:
                    doc = json.loads(line)
                    id, key = self.key(doc)
                    # XXX: if the line itself contains tabs, we need to remove
                    # them here; maybe offer TSV and JSON output and extra flag
                    print("{}\t{}\t{}".format(id, key, line.replace("\t", " ")), file=tf)
                except (KeyError, ValueError):
                    if strict:
                        raise
                    self.counter["key_err"] += 1
                else:
                    self.counter["key_ok"] += 1

        try:
            sf = self.sort(tf.name, opts='-k 2')
            with open(sf) as f:
                for doc in self.group_by(f, key=cut(f=1)):
                    self.counter["num_clusters"] += 1
                    json.dump(doc, self.output)
                    self.output.write("\n")
        except Exception as exc:
            raise
        finally:
            os.remove(sf)
            os.remove(tf.name)

        return self.counter

    def sort(self, filename: str, opts: str = "-k 2", fast: bool = True, mode: str = "w"):
        """
        Sort tabular file with sort(1), returns the filename of the sorted file.
        TODO: use separate /fast/tmp for sort.
        """
        with tempfile.NamedTemporaryFile(delete=False, mode=mode, prefix=self.prefix) as tf:
            env = os.environ.copy()
            env["TMPDIR"] = self.tmpdir
            if fast:
                env["LC_ALL"] = "C"
            subprocess.run(["sort"] + opts.split() + [filename], stdout=tf, env=env, check=True)

        return tf.name

    def group_by(self,
                 seq: collections.abc.Iterable,
                 key: Callable[[Any], str] = None) -> Generator[Any, None, None]:
        """
        Extract a key from elements of an iterable and group them. Just as
        uniq(1), the iterable must be ordered for this to work.
        """
        for k, g in itertools.groupby(seq, key=key):
            items = list(g)
            payload = []
            for line in items:
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
