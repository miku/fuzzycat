#!/usr/bin/env python
"""Usage: fuzzycat COMMAND [options]

Commands: cluster, verify

Run, e.g. fuzzycat cluster --help for more options. Example:

    $ zstdcat -T0 release_export_expanded.json.zst |
      parallel --tmpdir /fast/tmp --roundrobin --pipe -j 4 |
      python -m fuzzycat.main cluster --tmpdir /fast/tmp -t tnorm > clusters.jsonl
"""

import argparse
import logging
import sys
import tempfile

from fuzzycat.cluster import (Cluster, release_key_title, release_key_title_normalized,
                              release_key_title_nysiis)


def run_cluster(args):
    types = {
        'title': release_key_title,
        'tnorm': release_key_title_normalized,
        'tnysi': release_key_title_nysiis,
    }
    cluster = Cluster(files=args.files,
                      keyfunc=types.get(args.type),
                      tmpdir=args.tmpdir,
                      prefix=args.prefix)
    cluster.run()


def run_verify(args):
    print('verify')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(prog='fuzzycat',
                                     description=__doc__,
                                     usage='%(prog)s command [options]',
                                     add_help=False,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--prefix', default='fuzzycat-', help='temp file prefix')
    parser.add_argument('--tmpdir', default=tempfile.gettempdir(), help='temporary directory')
    subparsers = parser.add_subparsers()

    sub_cluster = subparsers.add_parser('cluster', help='group entities', parents=[parser])
    sub_cluster.set_defaults(func=run_cluster)
    sub_cluster.add_argument('-f', '--files', default="-", help='output files')
    sub_cluster.add_argument('-t',
                             '--type',
                             default='title',
                             help='cluster algorithm: title, tnorm, tnysi')

    sub_verify = subparsers.add_parser('verify', help='verify groups', parents=[parser])
    sub_verify.set_defaults(func=run_verify)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    args.func(args)
