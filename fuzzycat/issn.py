"""
Munge the ISSN data so we get some container name test data out of it.

      ...
      "issn": "0000-0019",
      "mainTitle": "<U+0098>The <U+009C>publishers weekly.",
      "name": [
        "<U+0098>The <U+009C>publishers weekly.",
        "Publishers weekly"
      ],

Public data from ISSN via:
https://portal.issn.org/resource/ISSN/0874-2308?format=json, and issnlister
(https://github.com/miku/issnlister) to aggregate.

The dataset contains naming variants in "name".

Q1: How many of these variants would our matching algorithm detect?

For that, we need a dataset that generates pairs (a, b) from all names (the
mainTitle is just one of the name).

"""

import argparse
import collections
import itertools
import json
import os
import sys
from typing import Iterable

from fuzzycat.utils import SetEncoder


def generate_name_pairs(lines: Iterable):
    """
    Given JSON lines, yield a tuple (issn, a, b) of test data. Will skip on
    errors.
    """
    for line in lines:
        line = line.strip()
        try:
            doc = json.loads(line)
        except json.decoder.JSONDecodeError as exc:
            print("failed to parse json: {}, data: {}".format(exc, line), file=sys.stderr)
            continue
        for item in doc.get("@graph", []):
            issn = item.get("issn", "")
            if not issn:
                continue
            if len(issn) != 9:
                continue
            if issn[4] != "-":
                continue
            names = item.get("name")
            if not names:
                continue
            if isinstance(names, str):
                names = [names]
            if not isinstance(names, list):
                raise ValueError("expected a list: {} {}".format(names, type(names)))
            if len(names) < 2:
                continue

            # Some names contain whitespace in the database, "      Mystery &
            # detection annual" -- control character prefixes (e.g. C2 98)
            # remain.
            names = [s.strip() for s in names]

            for a, b in itertools.combinations(names, 2):
                yield (issn, a, b)


def generate_name_issn_mapping(lines: Iterable):
    """
    Given JSON lines, generate a dictionary mapping names sets of ISSN. Names
    might be reused.
    """
    mapping = collections.defaultdict(set)
    for issn, a, b in generate_name_pairs(lines):
        mapping[a].add(issn)
        mapping[b].add(issn)
    return mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file",
                        default=sys.stdin,
                        type=argparse.FileType("r"),
                        help="public data from issn, one JSON object per line")
    parser.add_argument("--make-pairs",
                        action="store_true",
                        help="generate TSV and write to stdout")
    parser.add_argument("--make-mapping",
                        action="store_true",
                        help="generate JSON mapping from name to list of ISSN")
    parser.add_argument("--make-module",
                        action="store_true",
                        help="generate Python lookup table module and write to stdout")

    args = parser.parse_args()

    if args.make_mapping:
        print(json.dumps(generate_name_issn_mapping(args.file), cls=SetEncoder))

    if args.make_pairs:
        for issn, a, b in generate_name_pairs(args.file):
            print("{}\t{}\t{}".format(issn, a, b))
