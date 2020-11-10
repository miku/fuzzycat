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
import io
import logging
import pstats
# import json
import sys
import tempfile

import orjson as json

from fuzzycat.build import NgramLookup, TitleTokenList
from fuzzycat.cluster import (Cluster, release_key_title, release_key_title_normalized,
                              release_key_title_nysiis, release_key_title_ngram)


def run_cluster(args):
    logger = logging.getLogger('main.run_cluster')
    types = {
        'title': release_key_title,
        'tnorm': release_key_title_normalized,
        'tnysi': release_key_title_nysiis,
        'tss': release_key_title_ngram,
    }
    cluster = Cluster(files=args.files,
                      keyfunc=types.get(args.type),
                      tmpdir=args.tmpdir,
                      prefix=args.prefix)
    stats = cluster.run()
    logger.debug(json.dumps(dict(stats)))


def run_verify(args):
    """
    TODO.
    """
    print('verify')


def run_build(args):
    """
    Trying out.
    """
    if args.type == "ss":
        builder = NgramLookup(files=args.files, output=args.output)
        builder.run()
    elif args.type == "tt":
        builder = TitleTokenList(files=args.files, output=args.output)
        builder.run()
    else:
        raise NotImplementedError()


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
    sub_cluster.add_argument('-t',
                             '--type',
                             default='title',
                             help='cluster algorithm: title, tnorm, tnysi')

    sub_verify = subparsers.add_parser('verify', help='verify groups', parents=[parser])
    sub_verify.set_defaults(func=run_verify)

    sub_build = subparsers.add_parser('build', help='build auxiliary databases', parents=[parser])
    sub_build.add_argument('-f', '--files', default="-", help='input files')
    sub_build.add_argument('-t', '--type', default="ss", help='type of database to build')
    sub_build.add_argument('-o',
                           '--output',
                           type=argparse.FileType('w'),
                           default=sys.stdout,
                           help='output file')
    sub_build.set_defaults(func=run_build)

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
