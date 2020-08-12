# coding: utf-8

import collections
from typing import Any, Callable, DefaultDict, Dict, List

"""
A couple of utilities, may be split up into separate modules.
"""


class StringPipeline:
    """
    Minimalistic grouping of functions applied on an input string to produce
    some cleaned or normalized output. Pipeline functions are Func[[str], str].

        >>> cleanups = StringPipeline([
        ...     str.lower,
        ...     remove_html_tags,
        ...     normalize_whitespace,
        ...     normalize_ampersand,
        ... ])
        >>> cleanups.run("<a>Input  & Output</a>")
        input and output

    """

    def __init__(self, fs: List[Callable[[str], str]]):
        self.fs = fs

    def run(self, s: str) -> str:
        """
        Apply all function and return result.
        """
        for f in self.fs:
            s = f(s)
        return s


class StringAnnotator:
    """
    Experimental, rationale: In some way, feature engineering; we want to
    derive metrics, number from the string, do this consistently and compactly.
    E.g. once we have dozens of "speaking" characteristics, a case based method
    might become more readble.

    if s.is_single_token and s.some_ratio > 0.4:
        return MatchStatus.AMBIGIOUS

    Could also subclass string and pluck more methods on it (might be even
    reusable).

    ....

    Given a string, derive a couple of metrics, based on functions. The
    annotation is a dict, mapping an annotation key to a value of any type.

        >>> metrics = StringAnnotator([
        ...    has_html_tags,
        ...    has_only_printable_characters,
        ...    is_single_token,
        ...    length,
        ...    has_year_in_parentheses,
        ... ])
        >>> metrics.run("Journal of Pataphysics 2038-2032")
        {"value": "Journal of Pataphysics 2038-2032", "is_single_token": False, ... }

    TODO(martin):

    * SimpleNamespace, dotdict, Dataclass.
    * string_utils.py or similar
    * maybe adopt SpaCy or similar
    """

    def __init__(self, fs: List[Callable[[str], Dict[str, Any]]]):
        self.fs = fs

    def run(self, s: str) -> Dict[str, Any]:
        annotations: DefaultDict[str, Any] = collections.defaultdict(dict)
        for f in self.fs:
            result = f(s)
            annotations.update(result)
        return annotations
