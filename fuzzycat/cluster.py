"""
Clustering part of matching.

We want to have generic and fast way to derive various clusters. Input is a
json lines of release entities, e.g. from a database dump.

Map and reduce.

* input (json) blob -> (ident, value) -> group by value -> emit idents per group

"""

import argparse
import fileinput
import itertools
import json
import os
import subprocess
import tempfile
import re
import string

import orjson as json
import fuzzy

DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "fuzzycat")


def sort_by_column(filename, mode="w", opts="-k 2", fast=True):
    """
    Sort tabular file with sort(1), returns the filename of the sorted file.
    """
    with tempfile.NamedTemporaryFile(delete=False, mode=mode) as tf:
        env = os.environ.copy()
        if fast:
            env["LC_ALL"] = "C"
        subprocess.run(["sort"] + opts.split() + [filename], stdout=tf)

    return tf.name

def group_by_column(filename, key=None, value=None, comment=""):
    """
    Group a sorted file with given key function. Use another function to
    extract the value.
    """
    with open(filename) as f:
        for k, g in itertools.groupby(f, key=key):
            doc = {
                "v": [value(v) for v in g],
                "c": comment,
                "k": k.strip(),
            }
            yield doc

# XXX: LineOps

def cut(f=0, sep='\t'):
    """
    Similar to cut(1), but zero indexed.
    """
    return lambda v: v.split(sep)[f]

def cluster_by_title(args):
    """
    Basic example for a three stage process: extract, sort, group. Speed is
    about: 20K/s (json roundtrip, sorting, grouping).
    """
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tf:
        for line in fileinput.input(files=args.files if len(args.files) > 0 else ('-', )):
            doc = json.loads(line)
            try:
                id = doc["ident"]
                title = doc["title"]
                if not title:
                    continue
                else:
                    title = title.replace("\t", " ").replace("\n", " ").strip()
            except KeyError as err:
                continue
            print("%s\t%s" % (id, title), file=tf)

    sbc = sort_by_column(tf.name, opts="-k 2")
    for doc in group_by_column(sbc, key=cut(f=1), value=cut(f=0), comment="t"):
        print(json.dumps(doc).decode("utf-8"))

    os.remove(sbc)
    os.remove(tf.name)

def cluster_by_title_normalized(args):
    """
    Normalize title, e.g. analysisofheritability. 17k/s.
    """
    pattern = re.compile('[\W_]+', re.UNICODE)
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tf:
        for line in fileinput.input(files=args.files if len(args.files) > 0 else ('-', )):
            doc = json.loads(line)
            try:
                id = doc["ident"]
                title = doc["title"]
                if not title:
                    continue
                else:
                    title = title.replace("\t", " ").replace("\n", " ").strip().lower()
                    title = pattern.sub('', title)
            except KeyError as err:
                continue
            print("%s\t%s" % (id, title), file=tf)

    sbc = sort_by_column(tf.name, opts="-k 2")
    for doc in group_by_column(sbc, key=cut(f=1), value=cut(f=0), comment="t"):
        print(json.dumps(doc).decode("utf-8"))

    os.remove(sbc)
    os.remove(tf.name)

def cluster_by_title_nysiis(args):
    """
    Soundex on title.
    """
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tf:
        for line in fileinput.input(files=args.files if len(args.files) > 0 else ('-', )):
            doc = json.loads(line)
            try:
                id = doc["ident"]
                title = doc["title"]
                if not title:
                    continue
                else:
                    title = fuzzy.nysiis(title)
            except KeyError as err:
                continue

            print("%s\t%s" % (id, title))
            print("%s\t%s" % (id, title), file=tf)

    sbc = sort_by_column(tf.name, opts="-k 2")
    for doc in group_by_column(sbc, key=cut(f=1), value=cut(f=0), comment="t"):
        print(json.dumps(doc).decode("utf-8"))

    os.remove(sbc)
    os.remove(tf.name)

def main():
    types = {
        "title": cluster_by_title,
        "title_normalized": cluster_by_title_normalized,
        "title_nysiis": cluster_by_title_nysiis,
    }
    parser = argparse.ArgumentParser(prog='fuzzycat-cluster',
                                     usage='%(prog)s [options]',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-t", "--type", default="title", help="clustering variant to use")
    parser.add_argument("-l", "--list", action="store_true", help="list cluster variants")
    parser.add_argument('files', metavar='FILE', nargs='*', help='files to read, if empty, stdin is used')
    args = parser.parse_args()
    if args.list:
        print("\n".join(types.keys()))
        return
    func = types.get(args.type)
    if func is None:
        print("invalid type: {}".format(args.type))
        return
    func(args)
