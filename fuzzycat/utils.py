import collections
import io
import itertools
import os
import random
import re
import string
import subprocess
import tempfile

import requests
from glom import PathAccessError, glom
from zstandard import ZstdDecompressor

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


def zstdlines(filename, encoding="utf-8", bufsize=65536):
    """
    Generator over lines from a zstd compressed file.

    >>> for line in zstdlines("file.zst"):
    ...     print(line)

    """
    with open(filename, "rb") as f:
        decomp = ZstdDecompressor()
        with decomp.stream_reader(f) as reader:
            prev_line = ""
            while True:
                chunk = reader.read(bufsize)
                if not chunk:
                    break
                while True:
                    # We start with bytes but want unicode, which might not
                    # align; so we jitter around the end to complete the
                    # codepoint.
                    try:
                        string_data = chunk.decode(encoding)
                    except UnicodeDecodeError:
                        chunk = chunk + reader.read(1)
                    else:
                        break
                lines = string_data.split("\n")
                for i, line in enumerate(lines[:-1]):
                    if i == 0:
                        line = prev_line + line
                    yield line
                prev_line = lines[-1]


def shellout(template,
             preserve_whitespace=False,
             executable='/bin/bash',
             ignoremap=None,
             encoding=None,
             pipefail=True,
             **kwargs):
    """
    Takes a shell command template and executes it. The template must use the
    new (2.6+) format mini language. `kwargs` must contain any defined
    placeholder, only `output` is optional and will be autofilled with a
    temporary file if it used, but not specified explicitly.

    If `pipefail` is `False` no subshell environment will be spawned, where a
    failed pipe will cause an error as well. If `preserve_whitespace` is `True`,
    no whitespace normalization is performed. A custom shell executable name can
    be passed in `executable` and defaults to `/bin/bash`.

    Raises RuntimeError on nonzero exit codes. To ignore certain errors, pass a
    dictionary in `ignoremap`, with the error code to ignore as key and a string
    message as value.

    Simple template:

        wc -l < {input} > {output}

    Quoted curly braces:

        ps ax|awk '{{print $1}}' > {output}

    """
    if not 'output' in kwargs:
        kwargs.update({'output': tempfile.mkstemp(prefix='gluish-')[1]})
    if ignoremap is None:
        ignoremap = {}
    if encoding:
        command = template.decode(encoding).format(**kwargs)
    else:
        command = template.format(**kwargs)
    if not preserve_whitespace:
        command = re.sub('[ \t\n]+', ' ', command)
    if pipefail:
        command = '(set -o pipefail && %s)' % command
    code = subprocess.call([command], shell=True, executable=executable)
    if not code == 0:
        if code not in ignoremap:
            error = RuntimeError('%s exitcode: %s' % (command, code))
            error.code = code
            raise error
    return kwargs.get('output')
