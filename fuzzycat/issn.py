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
import sys
import re
from typing import Iterable, Dict, List, Union

from fuzzycat.utils import SetEncoder


def listify(v : Union[str, List[str]]) -> List[str]:
    """
    Sensible create a list.
    """
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return v

def jsonld_minimal(v: Dict) -> Dict:
    """
    Turn a JSON from issn.org into a smaller dict with a few core fields.

    Example result: {'issnl': '0008-2554', 'issns': {'0008-2554'}, 'names':
        ['Canada agriculture (Ottawa)', 'Canada agriculture.']}
    """
    items = v.get("@graph")
    if not items:
        return {}
    doc = {}
    for item in items:
        pass
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
                match = re.match(r"^resource/ISSN-L/([0-9]{4,4}-[0-9]{3,3}[0-9xX])$", item.get("exampleOfWork", ""))
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
    Convert to a minimal JSON format.
    """
    for line in lines:
        line = line.strip()
        try:
            doc = json.loads(line)
            doc = jsonld_minimal(doc)
        except json.decoder.JSONDecodeError as exc:
            print("failed to parse json: {}, data: {}".format(exc, line), file=sys.stderr)
            continue
        else:
            print(json.dumps(doc, cls=SetEncoder))

def generate_name_pairs(lines: Iterable):
    """
    Given JSON lines, yield a tuple (issn, a, b) of test data. Will skip on
    errors.
    """
    for line in lines:
        line = line.strip()
        try:
            doc = json.loads(line)
            doc = jsonld_minimal(doc)
        except json.decoder.JSONDecodeError as exc:
            print("failed to parse json: {}, data: {}".format(exc, line), file=sys.stderr)
            continue
        for issn in doc.get("issns", []):
            for a, b in itertools.combinations(doc.get("names", []), 2):
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
    parser.add_argument("--de-jsonld",
                        action="store_true",
                        help="break up the jsonld")

    args = parser.parse_args()

    if args.make_mapping:
        print(json.dumps(generate_name_issn_mapping(args.file), cls=SetEncoder))

    if args.make_pairs:
        for issn, a, b in generate_name_pairs(args.file):
            print("{}\t{}\t{}".format(issn, a, b))

    if args.de_jsonld:
        de_jsonld(args.file)
