import argparse
import elasticsearch
import tempfile
import sys

def run_cluster(args):
    print('cluster')

def run_verify(args):
    print('verify')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='fuzzycat',
                                     usage='%(prog)s command [options]',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--tmp-prefix', default='fuzzycat-', help='temp file prefix')
    parser.add_argument('--tmpdir', default=tempfile.gettempdir(), help='temporary directory')
    subparsers = parser.add_subparsers()

    sub_cluster = subparsers.add_parser('cluster', help='group entities')
    sub_cluster.set_defaults(func=run_cluster)
    sub_cluster.add_argument('-t', '--type', default='title', help='cluster algorithm')

    sub_verify = subparsers.add_parser('verify', help='verify groups')
    sub_verify.set_defaults(func=run_verify)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        print('fuzzycat: use -h or --help for usage', file=sys.stderr)
        sys.exit(1)

    args.func(args)

