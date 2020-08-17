# coding: utf-8

import collections
import itertools
import json
import re
import string
from typing import Any, Callable, DefaultDict, Dict, List, Optional, Sequence
"""
A couple of utilities, may be split up into separate modules.
"""


class SetEncoder(json.JSONEncoder):
    """
    Helper to encode python sets into JSON lists.
    So you can write something like this:
        json.dumps({"things": set([1, 2, 3])}, cls=SetEncoder)
    """
    def default(self, obj):
        """
        Decorate call to standard implementation.
        """
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


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
        >>> cleanups("<a>Input  & Output</a>")
        input and output

    """
    def __init__(self, fs: List[Callable[[str], str]]):
        self.fs = fs

    def __call__(self, s: str) -> str:
        return self.run(s)

    def run(self, s: str) -> str:
        """
        Apply all function and return result. Deprecated: just call the object.
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


def normalize_whitespace(s: str) -> str:
    """
    Remove trailing spaces and normalize whitespace.
    """
    return re.sub(r"\s{2,}", " ", s.strip())


def normalize_ampersand(s: str) -> str:
    """
    Normalize ampersand to and.
    """
    return s.replace(" & ", " and ")


def letter_to_non_letter_ratio(s: str) -> float:
    """
    Non letters are defined by printable w/o letters.
    """
    if len(s) == 0:
        return 0.0
    non_letters = set(string.printable) - set(string.ascii_letters)
    non_letter_count = sum(c in non_letters for c in s)
    return non_letter_count / len(s)


def alphanumeric_ratio(s: str) -> float:
    """
    Ratio of letters, digit and whitespace to total string length.
    """
    if len(s) == 0:
        return 0.0
    alphanumeric = set(string.ascii_letters) | set(string.digits) | set([" "])
    alphanumeric_count = sum(c in alphanumeric for c in s)
    return alphanumeric_count / len(s)


def alphanumeric_only(s: str) -> str:
    """
    Remove all non-alphanumeric content from string.
    """
    alphanumeric = set(string.ascii_letters) | set(string.digits) | set([" "])
    return "".join((c for c in s if c in alphanumeric))


def parenthesized_year(s: str) -> Optional[str]:
    """
    Return the year only, if it is in parentheses, e.g. Hello (2020).
    """
    match = re.search(r"[\(\[]\s*([12][\d]{3})\s*[\]\)]", s)
    if match:
        return match.group(1)
    return None


def has_non_letters_ratio(s: str, threshold: float = 0.4) -> bool:
    """
    Check the ratio of non-letters in a string, e.g. for things like "A.R.G.H"
    """
    if len(s) == 0:
        return False
    return (sum(c not in string.ascii_letters for c in s) / len(s)) > threshold


def is_single_word_printable(s: str) -> bool:
    """
    True, if s is a single token of printable characters.
    """
    return all(c in string.printable for c in s) and s.split() == 1


def extract_wikidata_qids(s: str) -> List[str]:
    """
    Given a string, extract all qids.
    """
    return re.findall(r"Q[0-9]{1,10}", s)


def extract_issns(s: str) -> List[str]:
    """
    Given a string return a list of valid ISSN.
    """
    pattern = r"[0-9]{4,4}-[0-9]{3,3}[0-9xX]"
    return [v for v in re.findall(pattern, s) if is_valid_issn(v)]


def longest_common_prefix(a: Sequence, b: Sequence) -> Sequence:
    """
    Return the longest common prefix of a and b. The length of the return value
    is at most min(len(a), len(b)).
    """
    a, b = sorted((a, b), key=len)
    for i, (u, v) in enumerate(zip(a, b)):
        if u != v:
            return a[:i]
    return a


def common_prefix_length_ratio(a: Sequence, b: Sequence) -> float:
    """
    Return a float between 0.0 and 1.0 expressing the ratio between the length
    of the common shared prefix to the length of the longest sequence.
    """
    maxlen = max(len(a), len(b))
    if maxlen == 0:
        return 0.0
    return len(longest_common_prefix(a, b)) / maxlen


def hamming_distance(s: str, t: str) -> int:
    """
    Return hamming distance of s and t.
    """
    return sum((u != v for u, v in itertools.zip_longest(s, t)))


def calculate_issn_checkdigit(s: str) -> str:
    """
    Given a string of length 7, return the ISSN check value (digit or X) as
    string.
    """
    if len(s) != 7:
        raise ValueError("seven digits required")
    ss = sum((int(digit) * f for digit, f in zip(s, range(8, 1, -1))))
    _, mod = divmod(ss, 11)
    checkdigit = 0 if mod == 0 else 11 - mod
    result = "X" if checkdigit == 10 else "{}".format(checkdigit)
    return result


def is_valid_issn(issn: str) -> bool:
    """
    Return True, if the ISSN is valid. This does not mean it is registered.
    """
    if "-" in issn:
        issn = issn.replace("-", "")
    if len(issn) != 8:
        raise ValueError("invalid issn length: {}".format(issn))
    checkdigit = calculate_issn_checkdigit(issn[:7])
    return issn[7] == "{}".format(checkdigit)


def keys_with_values(d: Dict) -> List[Any]:
    """
    Return all keys of a dictionary which have non-falsy values.
    """
    return [k for k, v in d.items() if v]
