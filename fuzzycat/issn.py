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
import sys
import os
import json
import itertools


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file",
                        default=sys.stdin,
                        type=argparse.FileType("r"),
                        help="public data from issn, one JSON object per line")
    parser.add_argument("--make-pairs", action="store_true")

    args = parser.parse_args()

    if args.make_pairs:
        for line in args.file:
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

                for a, b in itertools.combinations(names, 2):
                    print("{}\t{}\t{}".format(issn, a, b))
