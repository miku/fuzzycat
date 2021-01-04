import collections
import io
import itertools
import os
import random
import re
import string

import requests
from glom import PathAccessError, glom

printable_no_punct = string.digits + string.ascii_letters + string.whitespace

# More correct: https://www.johndcook.com/blog/2016/02/04/regular-expression-to-match-a-chemical-element/
CHEM_FORMULA = re.compile(r"([A-Z]{1,2}[0-9]{1,2})+")

ParsedPages = collections.namedtuple("ParsedPages", "start end count")


def parse_page_string(s):
    """
    Parse typical page strings, e.g. 150-180.
    """
    if not s:
        raise ValueError('page parsing: empty string')
    if s.isnumeric():
        return ParsedPages(start=int(s), end=int(s), count=1)
    page_pattern = re.compile("([0-9]{1,})-([0-9]{1,})")
    match = page_pattern.match(s)
    if not match:
        raise ValueError('cannot parse page pattern from {}'.format(s))
    start, end = match.groups()
    if len(end) == 1 and start and start[-1] < end:
        # 261-5, odd, but happens
        end = start[:-1] + end
    a, b = int(start), int(end)
    if a > b:
        raise ValueError('invalid page range: {}'.format(s))
    count = b - a + 1
    return ParsedPages(start=a, end=b, count=count)


def dict_key_exists(doc, path):
    """
    Return true, if key in a dictionary at a given path exists. XXX: probably
    already in glom.
    """
    try:
        _ = glom(doc, path)
    except PathAccessError:
        return False
    else:
        return True


def doi_prefix(v):
    """
    Return the prefix of a DOI.
    """
    return v.split("/")[0]


def has_doi_prefix(v, prefix="10.1234"):
    """
    Returns False, if we cannot parse v or prefix does not match.
    """
    if not v:
        return False
    return v.split("/")[0] == prefix


def slugify_string(s: str) -> str:
    """
    Keeps ascii chars and single whitespace only.
    """
    return ' '.join(''.join((c for c in s.lower() if c in printable_no_punct)).split())


def cut(f: int = 0, sep: str = '\t', ignore_missing_column: bool = True):
    """
    Return a callable that extracts a given column from a line.
    """
    def func(value):
        parts = value.strip().split(sep)
        if f >= len(parts):
            if ignore_missing_column:
                return ""
            raise ValueError('cannot split value {} into {} parts'.format(value, f))
        return parts[f]

    return func


def author_similarity_score(u, v):
    """
    Given two author strings, return a similarity score between 0 and 1.
    """
    return jaccard(set(token_n_grams(u)), set(token_n_grams(v)))


def jaccard(a, b):
    """
    Jaccard of sets a and b.
    """
    if len(a | b) == 0:
        return 0
    return len(a & b) / len(a | b)


def token_n_grams(s, n=2):
    """
    Return n-grams, calculated per token.
    """
    return ["".join(v) for v in itertools.chain(*[nwise(v, n=n) for v in tokenize_string(s)])]


def tokenize_string(s):
    """
    Normalize and tokenize, should be broken up.
    """
    return [token for token in s.lower().split()]


def nwise(iterable, n=2):
    """
    Generalized: func: `pairwise`. Split an iterable after every
    `n` items.
    """
    i = iter(iterable)
    piece = tuple(itertools.islice(i, n))
    while piece:
        yield piece
        piece = tuple(itertools.islice(i, n))


def num_project(s):
    """
    Cf. https://fatcat.wiki/release/6b5yupd7bfcw7gp73hjoavbgfq,
    https://fatcat.wiki/release/7hgzqz3hrngq7omtwdxz4qx34u

    Unify every occurence of a digit (or group of digits).
    """
    return re.sub(r'\d+', '<NUM>', s)


def contains_chemical_formula(s):
    """
    Returns true, if we find C3H8O or the like in title.
    """
    for token in s.split():
        if CHEM_FORMULA.search(token):
            return True


def random_word(func=lambda w: True, wordsfile='/usr/share/dict/words'):
    """
    Requires the UNIX words file in a typical location. Returns a single,
    random word.
    """
    if not os.path.exists(wordsfile):
        raise RuntimeError('file not found: {}'.format(wordsfile))
    with open(wordsfile) as f:
        words = list(filter(func, (word.strip() for word in f)))
    return random.choice(words)


def random_idents_from_query(query="*",
                             es="https://search.fatcat.wiki/fatcat_release/_search",
                             r=2):
    """
    Return a number of random idents from a search query.
    """
    resp = requests.get(es, params={"q": query})
    if resp.status_code != 200:
        raise RuntimeError('could not query {} for random item: {}'.format(es, r.url))
    payload = resp.json()
    if payload["hits"]["total"] < 2:
        raise RuntimeError('to few documents')
    idents = [doc["_source"]["ident"] for doc in payload["hits"]["hits"]]
    return random.sample(idents, r)
