"""
Clustering stage.
"""

import functools
import operator
import re
import sys

import fuzzy

__all__ = [
    "release_key_title",
    "release_key_title_normalized",
    "release_key_title_nysiis",
    "sort_file_by_column",
]

get_ident_title = operator.itemgetter("ident", "title")
ws_replacer = str.maketrans("\t", " ", "\n", " ")
non_word_re = re.compile('[\W_]+', re.UNICODE)

def cut(value, f=0, sep='\t'):
    """
    Split value by separator and return a single column.
    """
    return value.split(sep)[f]

def release_key_title(re):
    id, title = get_ident_title(re)
    if not title:
        raise ValueError('title missing')
    title = title.translate(ws_replacer).strip()
    return (id, title)

def release_key_title_normalized(re):
    id, title = release_key_title(re)
    return (id, non_word_re.sub('', title))

def release_key_title_nysiis(re):
    id, title = release_key_title(re)
    return (id, fuzzy.nysiis(title))

def sort_by_column(filename, opts="-k 2", fast=True, mode="w", prefix="fuzzycat-"):
    """
    Sort tabular file with sort(1), returns the filename of the sorted file.
    TODO: use separate /fast/tmp for sort.
    """
    with tempfile.NamedTemporaryFile(delete=False, mode=mode, prefix=prefix) as tf:
        env = os.environ.copy()
        if fast:
            env["LC_ALL"] = "C"
        subprocess.run(["sort"] + opts.split() + [filename], stdout=tf, env=env)

    return tf.name

def group_by(filename, key=None, value=None, comment=""):
    with open(filename) as f:
        for k, g in itertools.groupby(f, key=key):
            doc = {
                "k": k.strip(),
                "v": [value(v) for v in g],
                "c": comment,
            }
            yield doc

class Cluster:
    """
    Cluster scaffold for release entities.
    """
    def __init__(self, files=None, output=None, keyfunc=lambda v: v, tmp_prefix='fuzzycat-'):
        self.files = files
        self.tmp_prefix = tmp_prefix
        self.keyfunc = keyfunc
        self.output = output
        if self.output is None:
            self.output = sys.stdout

    def run(self):
        with tempfile.NamedTemporaryFile(delete=False, mode="w", prefix=self.tmp_prefix) as tf:
            for line in fileinput.input(files=files):
                try:
                    id, key = self.keyfunc(json.loads(line))
                except (KeyError, ValueError):
                    continue
                else:
                    print("{}\t{}".format(id, key), file=tf)

        sbc = sort_by_column(tf.name, opts='-k 2', prefix=self.tmp_prefix)
        for doc in group_by(sbc, key=cut(f=1), value=cut(f=0), comment=keyfunc.__name__):
            json.dump(doc, self.output)

        os.remove(sbc)
        os.remove(tf.name)
