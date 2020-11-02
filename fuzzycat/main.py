import argparse
import sys
import tempfile

import elasticsearch

from fuzzycat.cluster import (Cluster, release_key_title,
                              release_key_title_normalized,
                              release_key_title_nysiis)


def run_cluster(args):
    types = {
        'title': release_key_title,
        'tnorm': release_key_title_normalized,
        'tnysi': release_key_title_nysiis,
    }
    cluster = Cluster(files=args.files, keyfunc=types.get(args.type), tmpdir=args.tmpdir, prefix=args.prefix)


def run_verify(args):
    print('verify')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='fuzzycat',
                                     usage='%(prog)s command [options]',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--prefix', default='fuzzycat-', help='temp file prefix')
    parser.add_argument('--tmpdir', default=tempfile.gettempdir(), help='temporary directory')
    subparsers = parser.add_subparsers()

    sub_cluster = subparsers.add_parser('cluster', help='group entities')
    sub_cluster.set_defaults(func=run_cluster)
    sub_cluster.add_argument('-f', '--files', default="-", help='output files')
    sub_cluster.add_argument('-t', '--type', default='title', help='cluster algorithm')

    sub_verify = subparsers.add_parser('verify', help='verify groups')
    sub_verify.set_defaults(func=run_verify)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        print('fuzzycat: use -h or --help for usage', file=sys.stderr)
        sys.exit(1)

    args.func(args)
