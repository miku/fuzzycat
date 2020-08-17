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

Example JSON LD response from ISSN:

{
  "@context": {
    "format": {
      "@id": "http://purl.org/dc/elements/1.1/format",
      "@type": "@id"
    },
    "identifiedBy": {
      "@id": "http://id.loc.gov/ontologies/bibframe/identifiedBy",
      "@type": "@id"
    },
    "identifier": {
      "@id": "http://purl.org/dc/elements/1.1/identifier"
    },
    "isPartOf": {
      "@id": "http://schema.org/isPartOf",
      "@type": "@id"
    },
    "issn": {
      "@id": "http://purl.org/ontology/bibo/issn"
    },
    "label": {
      "@id": "http://www.w3.org/2000/01/rdf-schema#label"
    },
    "location": {
      "@id": "http://schema.org/location",
      "@type": "@id"
    },
    "mainEntity": {
      "@id": "http://schema.org/mainEntity",
      "@type": "@id"
    },
    "modified": {
      "@id": "http://purl.org/dc/terms/modified",
      "@type": "http://www.w3.org/2001/XMLSchema#dateTime"
    },
    "name": {
      "@id": "http://schema.org/name"
    },
    "publication": {
      "@id": "http://schema.org/publication",
      "@type": "@id"
    },
    "status": {
      "@id": "http://id.loc.gov/ontologies/bibframe/status",
      "@type": "@id"
    },
    "title": {
      "@id": "http://id.loc.gov/ontologies/bibframe/title",
      "@type": "@id"
    },
    "type": {
      "@id": "http://purl.org/dc/terms/type",
      "@type": "@id"
    },
    "value": {
      "@id": "http://www.w3.org/1999/02/22-rdf-syntax-ns#value"
    },
    "wasAttributedTo": {
      "@id": "http://www.w3.org/ns/prov#wasAttributedTo",
      "@type": "@id"
    }
  },
  "@graph": [
    {
      "@id": "http://id.loc.gov/vocabulary/countries/pl",
      "label": "Poland"
    },
    {
      "@id": "organization/ISSNCenter#57",
      "@type": "http://schema.org/Organization"
    },
    {
      "@id": "resource/ISSN-L/0001-4125",
      "identifiedBy": "resource/ISSN/0001-4125#ISSN-L"
    },
    {
      "@id": "resource/ISSN/0001-4125",
      "@type": [
        "http://schema.org/Periodical",
        "http://id.loc.gov/ontologies/bibframe/Instance",
        "http://id.loc.gov/ontologies/bibframe/Work"
      ],
      "format": "vocabularies/medium#Print",
      "http://schema.org/issn": "0001-4125",
      "identifiedBy": [
        "resource/ISSN/0001-4125#ISSN-L",
        "resource/ISSN/0001-4125#KeyTitle",
        "resource/ISSN/0001-4125#ISSN"
      ],
      "identifier": "0001-4125",
      "isPartOf": "resource/ISSN-L/0001-4125",
      "issn": "0001-4125",
      "name": "Bulletin de l'Académie Polonaise des Sciences. Série des Sciences Techniques",
      "publication": "resource/ISSN/0001-4125#ReferencePublicationEvent",
      "title": "resource/ISSN/0001-4125#KeyTitle",
      "type": "http://marc21rdf.info/terms/formofmaterial#a"
    },
    {
      "@id": "resource/ISSN/0001-4125#ISSN",
      "@type": "http://id.loc.gov/ontologies/bibframe/Issn",
      "status": "vocabularies/IdentifierStatus#Valid",
      "value": "0001-4125"
    },
    {
      "@id": "resource/ISSN/0001-4125#ISSN-L",
      "@type": "http://id.loc.gov/ontologies/bibframe/IssnL",
      "status": "vocabularies/IdentifierStatus#Valid",
      "value": "0001-4125"
    },
    {
      "@id": "resource/ISSN/0001-4125#KeyTitle",
      "@type": [
        "http://id.loc.gov/ontologies/bibframe/Identifier",
        "http://id.loc.gov/ontologies/bibframe/KeyTitle"
      ],
      "value": "Bulletin de l'Académie Polonaise des Sciences. Série des Sciences Techniques"
    },
    {
      "@id": "resource/ISSN/0001-4125#Record",
      "@type": "http://schema.org/CreativeWork",
      "mainEntity": "resource/ISSN/0001-4125",
      "modified": "20051223105700.0",
      "status": "vocabularies/RecordStatus#Register",
      "wasAttributedTo": "organization/ISSNCenter#57"
    },
    {
      "@id": "resource/ISSN/0001-4125#ReferencePublicationEvent",
      "@type": "http://schema.org/PublicationEvent",
      "location": "http://id.loc.gov/vocabulary/countries/pl"
    }
  ]
}

"""

import argparse
import collections
import itertools
import json
import os
import re
import shelve
import sys
from typing import Any, Callable, Dict, Generator, Iterable, List, Tuple, Union

from simhash import Simhash

from fuzzycat import cleanups
from fuzzycat.utils import SetEncoder


def listify(v: Union[str, List[str]]) -> List[str]:
    """
    Sensible create a list.
    """
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return v


def jsonld_minimal(v: Dict[str, Any]) -> Dict[str, Any]:
    """
    Turn a JSON from issn.org into a smaller dict with a few core fields.  Will
    fail, if no ISSN-L is found in the input.

    {
      "issnl": "0001-4125",
      "material": [],
      "issns": [
	"0001-4125"
      ],
      "urls": [],
      "names": [
	"Bulletin de l'Académie Polonaise des Sciences. Série des Sciences Techniques"
      ]
    }

    """
    items = v.get("@graph")
    if not items:
        return {}
    doc = {}
    for item in items:
        # "@id": "resource/ISSN-L/0001-4125"
        # "@id": "resource/ISSN/0001-4125"
        # ...
        id = item.get("@id")
        if not id:
            continue

        # ISSN-L
        match = re.match(r"^resource/ISSN-L/([0-9]{4,4}-[0-9]{3,3}[0-9xX])$", id)
        if match:
            doc["issnl"] = match.group(1)
            continue

        # The "main" issn entry.
        match = re.match(r"^resource/ISSN/([0-9]{4,4}-[0-9]{3,3}[0-9xX])$", id)
        if match:
            # if we do not have ISSN-L yet, check "exampleOfWork",
            # "resource/ISSN/2658-0705"
            if not "issnl" in doc:
                match = re.match(r"^resource/ISSN-L/([0-9]{4,4}-[0-9]{3,3}[0-9xX])$",
                                 item.get("exampleOfWork", ""))
                if match:
                    doc["issnl"] = match.group(1)

            # note material
            doc["material"] = listify(item.get("material", []))

            # collect ids
            issns = set([match.group(1)])
            if item.get("identifier"):
                issns.add(item.get("identifier"))
            if item.get("issn"):
                issns.add(item.get("issn"))
            doc["issns"] = issns
            # add urls
            doc["urls"] = listify(item.get("url", []))
            # add names, variants
            names = listify(item.get("name")) + listify(item.get("alternateName"))
            doc["names"] = list(set(names))

            # add related issn
            for v in listify(item.get("isFormatOf", [])):
                match = re.match(r"^resource/ISSN/([0-9]{4,4}-[0-9]{3,3}[0-9xX])$", v)
                if match:
                    doc["issns"].add(match.group(1))

    if "issnl" not in doc:
        raise ValueError("entry without issnl: {}".format(item))

    return doc


def de_jsonld(lines: Iterable):
    """
    Batch convert jsonld to minimal JSON and write to stdout.
    """
    for line in lines:
        line = line.strip()
        try:
            doc = jsonld_minimal(json.loads(line))
        except json.decoder.JSONDecodeError as exc:
            print("failed to parse json: {}, data: {}".format(exc, line), file=sys.stderr)
            continue
        else:
            print(json.dumps(doc, cls=SetEncoder))


def generate_name_pairs(lines: Iterable,
                        cleanup_pipeline: Callable[[str], str] = None,
                        keep_original: bool = True) -> Generator[Tuple[str, str, str], None, None]:
    """
    Given JSON lines, yield a tuple (issnl, a, b) of test data. Will skip on
    errors. Proto unit test data.

    Example output:

    0013-211X       Eendracht-bode (Tholen) Eendracht-bode.
    0012-7388       Dynamic maturity        Dynamic maturity.
    0012-6055       Drehpunkt.      Drehpunkt (Basel. 1968)

    Basically, these would be free test cases, since we would like to report
    "match" on most of these.

    That can be useful to detect various scripts refering to the same journal.

    0040-2249       Tehnika kino i televideniâ.     Tehnika kino i televideniâ
    0040-2249       Tehnika kino i televideniâ.     Техника кино и телевидения
    0040-2249       Tehnika kino i televideniâ.     Техника кино и телевидения.
    0040-2249       Tehnika kino i televideniâ      Техника кино и телевидения
    0040-2249       Tehnika kino i televideniâ      Техника кино и телевидения.
    0040-2249       Техника кино и телевидения      Техника кино и телевидения.

    If cleanup_pipeline is given, additionally add
    """
    for line in lines:
        line = line.strip()
        try:
            doc = jsonld_minimal(json.loads(line))
        except json.decoder.JSONDecodeError as exc:
            print("failed to parse json: {}, data: {}".format(exc, line), file=sys.stderr)
            continue
        for a, b in itertools.combinations(doc.get("names", []), 2):
            if cleanup_pipeline is None or (cleanup_pipeline is not None and keep_original):
                yield (doc["issnl"], a, b)
            if cleanup_pipeline:
                a = cleanup_pipeline(a)
                b = cleanup_pipeline(b)
                yield (doc["issnl"], a, b)


def generate_name_issn_mapping(lines: Iterable, cleanup_pipeline: Callable[[str], str] = None):
    """
    Given JSON lines, generate a dictionary mapping names sets of ISSN. Names
    might be reused.
    """
    mapping = collections.defaultdict(set)
    for issnl, a, b in generate_name_pairs(lines, cleanup_pipeline=cleanup_pipeline):
        mapping[a].add(issnl)
        mapping[b].add(issnl)
    return mapping


def generate_shelve(lines: Iterable, output: str, cleanup_pipeline: Callable[[str], str] = None):
    """
    Generate a persistent key value store from name issn mappings. 5015523
    entries, 1.1G take about 5min.
    """
    with shelve.open(output) as db:
        mapping = generate_name_issn_mapping(lines, cleanup_pipeline=cleanup_pipeline)
        for name, issnls in mapping.items():
            db[name] = issnls
        print("wrote {} keys to {}".format(len(db), output), file=sys.stderr)


def generate_simhash(lines: Iterable):
    """
    Print TSV with simhash values.

    Match and non-match count.

    1069447 1
     927120 0
    """
    for issnl, a, b in generate_name_pairs(lines):
        ha = Simhash(a).value
        hb = Simhash(b).value
        row = (issnl, 0 if ha == hb else 1, ha, hb)
        print("\t".join([str(v) for v in row]))


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
    parser.add_argument("--make-shelve",
                        action="store_true",
                        help="generate trie mapping from name to list of ISSN")
    parser.add_argument("--make-simhash", action="store_true", help="print out simhash value")
    parser.add_argument("-o",
                        "--output",
                        type=str,
                        default="output.file",
                        help="write output to file")
    parser.add_argument("-c", "--cleanup", type=str, default=None, help="cleanup pipeline name")
    parser.add_argument("--de-jsonld", action="store_true", help="break up the jsonld")

    args = parser.parse_args()

    # Add additional cleanup routines here.
    cleanup = dict(basic=cleanups.basic).get(args.cleanup)

    if args.make_mapping:
        print(
            json.dumps(generate_name_issn_mapping(args.file, cleanup_pipeline=cleanup),
                       cls=SetEncoder))
    if args.make_pairs:
        for issn, a, b in generate_name_pairs(args.file, cleanup_pipeline=cleanup):
            print("{}\t{}\t{}".format(issn, a, b))
    if args.de_jsonld:
        de_jsonld(args.file)
    if args.make_shelve:
        generate_shelve(args.file, output=args.output, cleanup_pipeline=cleanup)
    if args.make_simhash:
        generate_simhash(args.file)
