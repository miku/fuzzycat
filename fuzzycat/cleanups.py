"""
Various shared cleanup approaches.
"""

from fuzzycat.utils import (StringPipeline, normalize_ampersand, normalize_whitespace)

# These transformations should not affect the name or a journal.
basic = StringPipeline([
    str.lower,
    normalize_whitespace,
    normalize_ampersand,
    lambda v: v.rstrip("."),
])
