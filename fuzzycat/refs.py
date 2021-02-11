import collections
import itertools
import json
import operator
import sys

from glom import PathAccessError, glom

from fuzzycat.common import Reason, Status
from fuzzycat.verify import verify


def find_release_entity(docs):
    """
    Return one "pivot" release entity (i.e. that does not have
    "extra.skate.status == "ref").
    """
    for doc in docs:
        try:
            if glom(doc, "extra.skate.status") == "ref":
                continue
        except PathAccessError:
            return doc

    raise ValueError("docs do not contain any release")


def ref_entities(docs):
    """
    Genator yielding ref entities only.
    """
    for doc in docs:
        try:
            if glom(doc, "extra.skate.status") == "ref":
                # XXX: on the fly fix for int/str years
                release_year = doc.get("release_year")
                if release_year is not None and isinstance(release_year, str):
                    doc["release_year"] = int(release_year)
                yield doc
        except PathAccessError:
            continue


class RefsGroupVerifier:
    """
    A specific verifier for grouped releases and references. We do not need to
    pair-wise compare, just compare one release to all references.
    """
    def __init__(self, iterable: collections.abc.Iterable, verbose=False):
        self.iterable: collections.abc.Iterable = iterable
        self.verbose: bool = verbose
        self.counter: Counter = collections.Counter()

    def run(self):
        get_key_values = operator.itemgetter("k", "v")
        for i, line in enumerate(self.iterable):
            if i % 20000 == 0 and self.verbose:
                print(i, file=sys.stderr)
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            k, vs = get_key_values(doc)
            pivot = find_release_entity(vs)
            for entity in ref_entities(vs):
                result, reason = verify(pivot, entity)
                self.counter[reason] += 1
                print("https://fatcat.wiki/release/{}".format(pivot["ident"]),
                      "https://fatcat.wiki/release/{}".format(entity["ident"]), result, reason)

        self.counter["total"] = sum(v for _, v in self.counter.items())
