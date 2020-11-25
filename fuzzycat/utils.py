import io
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
