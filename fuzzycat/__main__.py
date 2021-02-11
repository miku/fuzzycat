#!/usr/bin/env python
"""Usage: fuzzycat COMMAND [options]

COMMANDS

    cluster
    verify
    verify_single
    verify_ref
    release_match

  Run, e.g. fuzzycat cluster --help for more options.

EXAMPLES

  Clustering with GNU parallel.

      $ zstdcat -T0 release_export_expanded.json.zst |
          parallel --tmpdir /fast/tmp --roundrobin --pipe -j 4 |
          python -m fuzzycat.main cluster --tmpdir /fast/tmp -t tnorm > clusters.jsonl

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

      $ python -m fuzzycat release_match -q "hello world"

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
import random
import sys
import tempfile

import requests
from fatcat_openapi_client import ReleaseEntity

from fuzzycat.cluster import (Cluster, release_key_title, release_key_title_ngram,
                              release_key_title_normalized, release_key_title_nysiis,
                              release_key_title_sandcrawler)
from fuzzycat.entities import entity_to_dict
from fuzzycat.matching import anything_to_entity, match_release_fuzzy
from fuzzycat.refs import RefsGroupVerifier
from fuzzycat.utils import random_idents_from_query, random_word
from fuzzycat.verify import GroupVerifier, verify

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def run_cluster(args):
    """
    Run clustering over release entities from database dump.
    """
    logger = logging.getLogger('main.run_cluster')
    types = {
        'title': release_key_title,
        'tnorm': release_key_title_normalized,
        'tnysi': release_key_title_nysiis,
        'tss': release_key_title_ngram,
        'tsandcrawler': release_key_title_sandcrawler,
    }
    key_denylist = None
    if args.key_denylist:
        with open(args.key_denylist, 'r') as f:
            key_denylist = [l.strip() for l in f.readlines()]
    cluster = Cluster(iterable=fileinput.input(args.files),
                      key=types.get(args.type),
                      tmpdir=args.tmpdir,
                      compress=args.compress,
                      key_denylist=key_denylist,
                      prefix=args.prefix)
    cluster.run()
    logger.debug(json.dumps(dict(cluster.counter)))


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

    sub_cluster = subparsers.add_parser('cluster', help='group entities', parents=[parser])
    sub_cluster.set_defaults(func=run_cluster)
    sub_cluster.add_argument('-C',
                             '--compress',
                             action="store_true",
                             help='compress intermediate results')
    sub_cluster.add_argument('-f', '--files', default="-", help='input files')
    sub_cluster.add_argument('--key-denylist', help='file path to key denylist')
    sub_cluster.add_argument('--min-cluster-size',
                             default=2,
                             type=int,
                             help='ignore smaller clusters')
    sub_cluster.add_argument('-t',
                             '--type',
                             default='title',
                             help='cluster algorithm: title, tnorm, tnysi, tss, tsandcrawler')

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
