import re
import string

from ftfy import fix_text
from unidecode import unidecode

from fuzzycat.status import MatchStatus
from fuzzycat.utils import *


def match_container_names(a: str, b: str) -> MatchStatus:
    """
    Given two strings representing container names, return a match status.
    TODO(martin): incorporate abbreviations mapping, other synonyms.

    Some name stats over 146302 real names from fatcat.

        In [11]: len(df)
        Out[11]: 146302

        In [12]: df.head()
        Out[12]:
                                                        name  nlen
        0                       Sartre Studies International    28
        1                                Revolutionary world    19
        2  Monograph Series on Nonlinear Science and Comp...    52
        3                                  Hepatitis Monthly    17
        4                                             TRACEY     6

        In [13]: df.describe()
        Out[13]:
                        nlen
        count  146302.000000
        mean       33.891861
        std        18.955551
        min         2.000000
        25%        20.000000
        50%        31.000000
        75%        44.000000
        max       286.000000

    Aroung 4000 names which are not [a-zA-z ], e.g.:

        In [23]: df[df.is_alpha_only == False].sample(n=5)
        Out[23]:
                                                             name  nlen  is_alpha_only
        118497                     Журнал Фронтирных Исследований    30          False
        124885  Õpetatud Eesti Seltsi Aastaraamat/Yearbook of ...    74          False
        142217             Études économiques de l'OCDE : Norvège    38          False
        34681             حولیة کلیة أصول الدین والدعوة بالمنوفیة    39          False
        132251  Известия Российской академии наук Теория и сис...    61          False

    """

    if a is None or b is None:
        raise ValueError("strings required, got: a = {}, b = {}".format(a, b))

    # Basic normalisation, try to remove superfluous whitespace, which should
    # never matter, "HNO    Praxis"
    string_cleanups = StringPipeline([
        str.lower,
        str.strip,
        fix_text,
        lambda s: re.sub(r"\s{2,}", " ", s),
        lambda s: s.replace("&", "and"),
    ])
    a = string_cleanups.run(a)
    b = string_cleanups.run(b)

    # Derive some characteristics of the string. The keys are free form which
    # may or may not be a problem. TODO(martin): maybe subclass str and just
    # add additional methods?
    sa = StringAnnotator([
        lambda s: {
            "is_short_string": len(s) < 15
        },
        lambda s: {
            "is_printable_only": all(c in string.printable for c in s)
        },
        lambda s: {
            "is_single_token": len(s.split()) < 2
        },
        lambda s: {
            "letter_to_non_letter_ratio": letter_to_non_letter_ratio(s)
        },
        lambda s: {
            "alphanumeric_ratio": alphanumeric_ratio(s)
        },
        lambda s: {
            "has_diacritics": s != unidecode(s)
        },
        lambda s: {
            "startswith_the": s.startswith("the ")
        },
        lambda s: {
            "parenthesized_year": parenthesized_year(s)
        },
        lambda s: {
            "alphanumeric_only": alphanumeric_only(s)
        },
    ])
    asa = sa.run(a)
    bsa = sa.run(b)

    if asa["is_short_string"] and asa["letter_to_non_letter_ratio"] > 0.4:
        if a == b:
            return MatchStatus.EXACT

    if not asa["is_short_string"] and not asa["is_single_token"]:
        if a == b:
            return MatchStatus.EXACT

    # Short, single (ascii) word titles, like "Language" and the like. Single
    # token "臨床皮膚科" needs to pass.
    if asa["is_printable_only"] and asa["is_single_token"]:
        return MatchStatus.AMBIGIOUS

    if a == b:
        return MatchStatus.EXACT

    # Mostly ASCII, but with some possible artifacts.
    if (asa["alphanumeric_ratio"] > 0.9 and asa["alphanumeric_only"] == bsa["alphanumeric_only"]):
        return MatchStatus.STRONG

    # Year in parentheses case, e.g. "Conf X (2018)" and "Conf X (2019)" should
    # be different; about 3% of names contain a '(', 1% some possible date.
    if (asa["parenthesized_year"] and asa["parenthesized_year"] == bsa["parenthesized_year"]):
        return MatchStatus.DIFFERENT

    # Common prefixes (maybe curate these manually):
    common_prefixes = ("precarpathian bulletin of the shevchenko scientific society", )
    for prefix in common_prefixes:
        if a.startswith(prefix) and a != b:
            return MatchStatus.DIFFERENT

    if (not asa["is_short"] and not bsa["is_short"] and common_prefix_length_ratio(a, b) > 0.9):
        return MatchStatus.STRONG

    if (not asa["is_short"] and not bsa["is_short"] and common_prefix_length_ratio(a, b) > 0.7):
        return MatchStatus.WEAK

    # Address e.g. a char flip, but only, if we do not have diacritics.
    if (not asa["is_short_string"] and not asa["is_single_token"] and not asa["has_diacritics"] and hamming_distance(a, b) < 2):
        return MatchStatus.STRONG

    return MatchStatus.AMBIGIOUS
