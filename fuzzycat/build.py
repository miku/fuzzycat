"""
Build auxiliary data structures.
"""

import fileinput
import operator
import sqlite3
import string
import sys
import tempfile

import orjson as json
from nltk import word_tokenize
from nltk.corpus import stopwords

__all__ = [
    "sqlite3db",
    "NgramLookup",
]


class sqlitedb():
    """
    Simple cursor context manager for sqlite3 databases. Commits everything at exit.

        with sqlitedb('/tmp/test.db') as cursor:
            query = cursor.execute('SELECT * FROM items')
            result = query.fetchall()
    """
    def __init__(self, path, timeout=5.0, detect_types=0):
        self.path = path
        self.conn = None
        self.cursor = None
        self.timeout = timeout
        self.detect_types = detect_types

    def __enter__(self):
        self.conn = sqlite3.connect(self.path, timeout=self.timeout, detect_types=self.detect_types)
        self.conn.text_factory = str
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_class, exc, traceback):
        self.conn.commit()
        self.conn.close()


class TitleTokenList:
    """
    Build title token list.
    """
    def __init__(self, files="-", output=sys.stdout):
        self.files = files
        self.output = output
        self.stopwords = stopwords.words('english') + list(
            string.punctuation) + ["'", '"', "''", "`", "``"]

    def run(self):
        for i, line in enumerate(fileinput.input(files=self.files)):
            if i % 1000000 == 0:
                print("@{}".format(i), file=sys.stderr)
            try:
                doc = json.loads(line)
                title = doc["title"]
                tokens = [tok for tok in word_tokenize(title.lower()) if tok not in self.stopwords]
                self.output.write(json.dumps(tokens).decode("utf-8") + "\n")
            except KeyError:
                print("skipping doc w/o title: {}".format(line), file=sys.stderr)


class NgramLookup:
    """
    Outline:

    * tokenize title
    * remove stopwords
    * take first N, last N
    * tokenize first author

    Build aux sqlite3 db.

    Need to write out all data, the sort, the finalize as db.
    """
    def __init__(self, files="-", output="data.db", n=3):
        self.files = files
        self.output = output
        self.stopwords = stopwords.words('english') + list(
            string.punctuation) + ["'", '"', "''", "``", "'s", "→"]
        self.n = n

    def run(self):
        fast_fields = operator.itemgetter("ident", "title")
        for i, line in enumerate(fileinput.input(files=self.files)):
            if i % 10000 == 0:
                print("@{}".format(i), file=sys.stderr)
            try:
                doc = json.loads(line)
                id, title = fast_fields(doc)
                tokens = [tok for tok in word_tokenize(title.lower()) if tok not in self.stopwords]
                prefix = "-".join(tokens[:self.n])
                suffix = "-".join(tokens[-self.n:])
                print("{}\t{}\t{}".format(id, prefix, suffix))
            except KeyError as exc:
                print("skipping doc w/o title: {} - {}".format(line, exc), file=sys.stderr)
