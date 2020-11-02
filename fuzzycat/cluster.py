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
    "group_by",
]

get_ident_title = operator.itemgetter("ident", "title")
ws_replacer = str.maketrans({"\t": " ", "\n": " "})
non_word_re = re.compile('[\W_]+', re.UNICODE)

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

def sort_by_column(filename, opts="-k 2", fast=True, mode="w", prefix="fuzzycat-", tmpdir=None):
    """
    Sort tabular file with sort(1), returns the filename of the sorted file.
    TODO: use separate /fast/tmp for sort.
    """
    with tempfile.NamedTemporaryFile(delete=False, mode=mode, prefix=prefix) as tf:
        env = os.environ.copy()
        if tmpdir is not None:
            env["TMPDIR"] = tmpdir
        if fast:
            env["LC_ALL"] = "C"
        subprocess.run(["sort"] + opts.split() + [filename], stdout=tf, env=env)

    return tf.name

def group_by(filename, key=None, value=None, comment=""):
    """
    Iterate over lines in filename, group by key (a callable deriving the key
    from the line), then apply value callable to emit a minimal document.
    """
    with open(filename) as f:
        for k, g in itertools.groupby(f, key=key):
            doc = {
                "k": k.strip(),
                "v": [value(v) for v in g],
                "c": comment,
            }
            yield doc

def cut(f=0, sep='\t'):
    """
    Return a callable, that extracts a given column from a file with a specific
    separator. TODO: move this into more generic place.
    """
    def f(value):
        parts = value.split(sep)
        if len(parts) > f + 1:
            raise ValueError('cannot split value into {} parts'.format(f))
        return parts[f]
    return f

class Cluster:
    """
    Cluster scaffold for release entities.
    """
    def __init__(self, files="-", output=sys.stdout, keyfunc=lambda v: v, prefix='fuzzycat-', tmpdir=None):
        """
        Files can be a list of files or "-" for stdin.
        """
        self.files = files
        self.keyfunc = keyfunc
        self.output = output
        self.prefix = prefix
        self.tmpdir = tmpdir

    def run(self):
        """
        Run clustering and write output to given stream or file.
        """
        keyfunc = self.keyfunc # Save a lookup in loop.
        with tempfile.NamedTemporaryFile(delete=False, mode="w", prefix=self.prefix) as tf:
            for line in fileinput.input(files=files):
                try:
                    id, key = keyfunc(json.loads(line))
                    print("{}\t{}".format(id, key), file=tf)
                except (KeyError, ValueError):
                    continue
        sbc = sort_by_column(tf.name, opts='-k 2', prefix=self.prefix, tmpdir=self.tmpdir)
        for doc in group_by(sbc, key=cut(f=1), value=cut(f=0), comment=keyfunc.__name__):
            json.dump(doc, self.output)

        os.remove(sbc)
        os.remove(tf.name)
