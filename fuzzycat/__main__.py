#!/usr/bin/env python
"""Usage: fuzzycat COMMAND [options]

Commands: cluster, verify

Run, e.g. fuzzycat cluster --help for more options. Example:

    $ zstdcat -T0 release_export_expanded.json.zst |
      parallel --tmpdir /fast/tmp --roundrobin --pipe -j 4 |
      python -m fuzzycat.main cluster --tmpdir /fast/tmp -t tnorm > clusters.jsonl
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

from fuzzycat.cluster import (Cluster, release_key_title, release_key_title_ngram,
                              release_key_title_normalized, release_key_title_nysiis,
                              release_key_title_sandcrawler)
from fuzzycat.utils import random_idents_from_query, random_word
from fuzzycat.verify import GroupVerifier, verify

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def run_cluster(args):
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
                      key_denylist=key_denylist,
                      prefix=args.prefix)
    cluster.run()
    logger.debug(json.dumps(dict(cluster.counter)))


def run_verify(args):
    """
    TODO. Ok, we should not fetch data we have on disk (at the clustering
    step).
    """
    gv = GroupVerifier(iterable=fileinput.input(files=args.files))
    gv.run()


def run_verify_single(args):
    """
    Run a single verification on a pair.
    """
    result = {}
    if args.a and args.b:
        a, b = args.a, args.b
    elif not args.a and not args.b:
        for _ in range(10):
            word = random_word(wordsfile='/usr/share/dict/words')
            try:
                idents = random_idents_from_query(query=word, r=2)
            except RuntimeError:
                continue
            result.update({"extra": {"q": "https://fatcat.wiki/release/search?q={}".format(word)}})
            a, b = idents
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


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    parser = argparse.ArgumentParser(prog='fuzzycat',
                                     description=__doc__,
                                     usage='%(prog)s command [options]',
                                     add_help=False,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--prefix', default='fuzzycat-', help='temp file prefix')
    parser.add_argument('--tmpdir', default=tempfile.gettempdir(), help='temporary directory')
    parser.add_argument('-P', '--profile', action='store_true', help='profile program')
    subparsers = parser.add_subparsers()

    sub_cluster = subparsers.add_parser('cluster', help='group entities', parents=[parser])
    sub_cluster.set_defaults(func=run_cluster)
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
    sub_verify.set_defaults(func=run_verify)

    sub_verify_single = subparsers.add_parser('verify-single',
                                              help='verify a single pair',
                                              parents=[parser])
    sub_verify_single.add_argument('-a', help='ident or url to release')
    sub_verify_single.add_argument('-b', help='ident or url to release')
    sub_verify_single.set_defaults(func=run_verify_single)

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
