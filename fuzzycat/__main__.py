#!/usr/bin/env python
"""Usage: fuzzycat COMMAND [options]

COMMANDS

    verify
    verify_single
    verify_ref
    release_match
    unstructured

EXAMPLES

  Bulk verification.

      $ zstdcat -T0 cluster_tsandcrawler.json.zst |
          python -m fuzzycat verify | zstd -c9 > verify.tsv.zst

  Verify a randomly selected pair.

      $ python -m fuzzycat verify-single | jq .
      {
        "extra": {
  	"q": "https://fatcat.wiki/release/search?q=processes"
        },
        "a": "https://fatcat.wiki/release/r7c33wa4frhx3lgzb3jejd7ijm",
        "b": "https://fatcat.wiki/release/g6uqzmnt3zgald6blizi6x2wz4",
        "r": [
  	"different",
  	"num_diff"
        ]
      }

  Verify clustered refs:

      $ python -m fuzzycat verify-ref

  Release match (non-bulk).

      $ python -m fuzzycat release_match --value "hello world"

      TODO: Elasticsearch might not respond to POST queries (which is what the
      client library uses, see: https://git.io/JLssk).

"""

import argparse
import cProfile as profile
import fileinput
import io
import json
import logging
import pstats
import sys
import tempfile

import elasticsearch
import requests
from fatcat_openapi_client import ReleaseEntity

from fuzzycat.entities import entity_to_dict
from fuzzycat.grobid_unstructured import grobid_parse_unstructured
from fuzzycat.matching import anything_to_entity, match_release_fuzzy
from fuzzycat.refs import RefsGroupVerifier
from fuzzycat.simple import closest_fuzzy_release_match
from fuzzycat.utils import random_idents_from_query, random_word
from fuzzycat.verify import GroupVerifier, verify

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def run_verify(args):
    """
    Run match verification over dataset from clustering step.
    """
    verifier = GroupVerifier(iterable=fileinput.input(files=args.files),
                             verbose=args.verbose,
                             max_cluster_size=args.max_cluster_size)
    verifier.run()


def run_verify_single(args):
    """
    Run a single verification on a pair (or on a random pair, if none given).

    $ python -m fuzzycat verify-single | jq .
    {
      "extra": {
	"q": "https://fatcat.wiki/release/search?q=processes"
      },
      "a": "https://fatcat.wiki/release/r7c33wa4frhx3lgzb3jejd7ijm",
      "b": "https://fatcat.wiki/release/g6uqzmnt3zgald6blizi6x2wz4",
      "r": [
	"different",
	"num_diff"
      ]
    }

    """
    result = {}
    if args.a and args.b:
        a, b = args.a, args.b
    elif not args.a and not args.b:
        for _ in range(10):
            # We try a few times, since not all random words might yield
            # results.
            word = random_word(wordsfile='/usr/share/dict/words')
            try:
                idents = random_idents_from_query(query=word, r=2)
                result.update(
                    {"extra": {
                        "q": "https://fatcat.wiki/release/search?q={}".format(word)
                    }})
                a, b = idents
            except RuntimeError:
                continue
            break
        else:
            raise RuntimeError('could not fetch random releases')
    else:
        raise ValueError('specify either both -a, -b or none')

    def fetch_ident(ident):
        return requests.get("https://api.fatcat.wiki/v0/release/{}".format(ident)).json()

    result.update({
        "a": "https://fatcat.wiki/release/{}".format(a),
        "b": "https://fatcat.wiki/release/{}".format(b),
        "r": verify(fetch_ident(a), fetch_ident(b)),
    })
    print(json.dumps(result))


def run_ref_verify(args):
    verifier = RefsGroupVerifier(iterable=fileinput.input(files=args.files), verbose=args.verbose)
    verifier.run()


def run_release_match(args):
    """
    Given a release, return similar releases.
    """
    try:
        entity = anything_to_entity(args.value, ReleaseEntity)
        result = match_release_fuzzy(entity, size=args.size, es=args.es_url)
    except Exception as err:
        print("fuzzy match failed: {}".format(err), file=sys.stderr)
    else:
        if args.output_format == "tsv":
            for ce in result:
                vs = [ce.ident, ce.work_id, ce.container_id, ce.title]
                print("\t".join((str(v) for v in vs)))
        if args.output_format == "json":
            matches = []
            for ce in result:
                vs = {
                    "ident": ce.ident,
                    "work_id": ce.work_id,
                    "container_id": ce.container_id,
                    "title": ce.title,
                }
                matches.append(vs)
            vs = {"entity": entity_to_dict(entity), "matches": matches, "match_count": len(matches)}
            print(json.dumps(vs))


def run_unstructured(args):
    """
    Given a raw citation string, parse it and find "closest" match.

    Uses lower-level routines instead of simple.closest_fuzzy_unstructured_match(raw_citation)
    """
    es_client = elasticsearch.Elasticsearch(args.es_url)

    print("## Sending to GROBID...", file=sys.stderr)
    release = grobid_parse_unstructured(args.raw_citation)
    if not release:
        print("Did not parse")
        sys.exit(-1)
    else:
        print(entity_to_dict(release))
    print("## Fuzzy matching...", file=sys.stderr)
    closest = closest_fuzzy_release_match(release, es_client=es_client)
    if not closest:
        print("Did not match/verify")
        sys.exit(-1)
    print(f"{closest.status.name}\t{closest.reason.name}\trelease_{closest.release.ident}")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    # TODO: group flags sensibly
    parser = argparse.ArgumentParser(prog='fuzzycat',
                                     description=__doc__,
                                     usage='%(prog)s command [options]',
                                     add_help=False,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--prefix', default='fuzzycat-', help='temp file prefix')
    parser.add_argument('--tmpdir', default=tempfile.gettempdir(), help='temporary directory')
    parser.add_argument('-P', '--profile', action='store_true', help='profile program')
    parser.add_argument("--es-url",
                        default="https://search.fatcat.wiki",
                        help="fatcat elasticsearch")
    parser.add_argument("-m",
                        "--output-format",
                        help="output format, e.g. tsv or json",
                        default="tsv")
    parser.add_argument("-s", "--size", help="number of results to return", default=5, type=int)
    parser.add_argument("-v", "--verbose", help="be verbose", action='store_true')
    subparsers = parser.add_subparsers()

    sub_verify = subparsers.add_parser('verify', help='verify groups', parents=[parser])
    sub_verify.add_argument('-f', '--files', default="-", help='input files')
    sub_verify.add_argument('--max-cluster-size',
                            default=10,
                            type=int,
                            help='ignore large clusters')
    sub_verify.set_defaults(func=run_verify)

    sub_verify_single = subparsers.add_parser('verify_single',
                                              help='verify a single pair',
                                              parents=[parser])
    sub_verify_single.add_argument('-a', help='ident or url to release')
    sub_verify_single.add_argument('-b', help='ident or url to release')
    sub_verify_single.set_defaults(func=run_verify_single)

    sub_ref_verify = subparsers.add_parser('verify_ref', help='verify ref groups', parents=[parser])
    sub_ref_verify.add_argument('-f', '--files', default="-", help='input files')
    sub_ref_verify.set_defaults(func=run_ref_verify)

    sub_release_match = subparsers.add_parser(
        "release_match",
        help="find release matches",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[parser])

    sub_release_match.add_argument(
        "--value",
        help="release title, issn, QID, filename to entity JSON, or JSON lines",
        default="hello world",
        type=str,
    )
    sub_release_match.set_defaults(func=run_release_match)

    sub_unstructured = subparsers.add_parser("unstructured",
                                             help="parse and match unstructured citation string",
                                             formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    sub_unstructured.add_argument(
        "raw_citation",
        help="unstructured/raw citation string",
        type=str,
    )
    sub_unstructured.set_defaults(func=run_unstructured)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    if args.profile:
        logging.disable(logging.DEBUG)
        pr = profile.Profile()
        pr.enable()

    args.func(args)

    if args.profile:
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        print(s.getvalue(), file=sys.stderr)
