import io
import itertools
import string

printable_no_punct = string.digits + string.ascii_letters + string.whitespace


def slugify_string(s: str) -> str:
    """
    Keeps ascii chars and single whitespace only.
    """
    return ''.join((c for c in s.lower() if c in printable_no_punct))


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
