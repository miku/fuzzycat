"""
Verification part of matching.

We represent clusters as json lines. One example input line:

    {
      "v": [
        {...}, ...
      ],
      "k": "1 Grundlagen",
    }

Examples from clustering stage (from a sample of 100k records):

    ["Global residue formula for logarithmic indices of foliations",2]
    ["Glossary",8]
    ["Gordonia sp.",4]
    ["ERRATA",6]
    ["ERRATUM",4]
    ["Editor's Note",8]
    ["Editorial",95]
    ["Editorial Board",154]
    ["Editorial Board & Publication Information",2]
    ...

"""

import collections
import itertools
import json
import operator
import sys
from enum import Enum

from fuzzycat.cluster import slugify_string

get_key_values = operator.itemgetter("k", "v")

# There titles appear too often, so ignore them for now.
TITLE_BLACKLIST = set([
    "",
    "actualités",
    "about this issue",
    "about this journal",
    "abbreviations and acronyms",
    "acknowledgment of reviewers",
    "abbildung",
    "abstracts",
    "acknowledgements",
    "acknowledgments",
    "announcement",
    "announcements",
    "arthrobacter sp.",
    "author index",
    "back matter",
    "backmatter",
    "bibliography",
    "book review",
    "book reviews",
    "books received",
    "calendar",
    "conclusion",
    "conclusions",
    "contents",
    "contributors",
    "copyright",
    "correction",
    "correspondence",
    "corrigendum",
    "cover",
    "dedication",
    "discussion",
    "editorial",
    "editorial board",
    "einleitung",
    "erratum",
    "foreword",
    "front cover",
    "front matter",
    "frontmatter",
    "gbif occurrence download",
    "index",
    "inhalt",
    "in this issue",
    "introduction",
    "issue information",
    "letters to the editor",
    "letter to the editor",
    "masthead",
    "miscellany",
    "news",
    "not available",
    "notes",
    "occurrence download",
    "[others]",
    "oup accepted manuscript",
    "petitions.xlsx",
    "preface",
    "preliminary material",
    "preservation image",
    "references",
    "reply",
    "reviews",
    "reviews of books",
    "short notices",
    "[s.n.]",
    "streptomyces sp.",
    "subject index",
    "table of contents",
    "taxonomic abstract for the species.",
    "the applause data release 2",
    ":{unav)",
    "奥付",
    "投稿規定",
    "目次",
    "表紙",
    "裏表紙",
])


class Status(str, Enum):
    """
    Match status.
    """
    EXACT = 'exact'
    DIFFERENT = 'different'
    STRONG = 'strong'
    WEAK = 'weak'
    AMBIGUOUS = 'ambigiuous'


class OK(str, Enum):
    """
    Reason for assuming we have a match.
    """
    ARXIV_VERSION = 'ok.arxiv_version'
    DUMMY = 'ok.dummy'
    TITLE_AUTHOR_MATCH = 'ok.title_author_match'
    PREPRINT_PUBLISHED = 'ok.preprint_published'


class Miss(str, Enum):
    """
    Reasons indicating mismatch.
    """
    ARXIV_VERSION = 'miss.arxiv_version'
    BLACKLISTED = 'miss.blacklisted'
    CONTRIB_INTERSECTION_EMPTY = 'miss.contrib_intersection_empty'
    SHORT_TITLE = 'miss.short_title'
    YEAR = 'miss.year'
    CUSTOM_VHS = 'miss.vhs' # https://fatcat.wiki/release/44gk5ben5vghljq6twm7lwmxla


class GroupVerifier:
    """
    Verifier.

    Within a group, we could have multiple sub clusters, e.g.

    > [AABAB]

    We would need to compare each possible pair and decide whether they are the
    same.
    """
    def __init__(self, iterable: collections.abc.Iterable, max_cluster_size: int = 10):
        self.iterable: collections.abc.Iterable = iterable
        self.max_cluster_size: int = 10
        self.counter = collections.Counter()

    def run(self):
        for i, line in enumerate(self.iterable):
            if i % 20000 == 0:
                print(i, file=sys.stderr)
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            k, vs = get_key_values(doc)
            if len(vs) < 2:
                self.counter["unique"] += 1
                continue
            if len(vs) > self.max_cluster_size:
                self.counter["too_large"] += 1
                continue
            for a, b in itertools.combinations(vs, r=2):
                result, reason = compare(a, b)
                self.counter[reason] += 1
                print("https://fatcat.wiki/release/{}".format(a["ident"]),
                      "https://fatcat.wiki/release/{}".format(b["ident"]), result, reason)

        self.counter["total"] = sum(v for _, v in self.counter.items())
        print(json.dumps(dict(self.counter)), file=sys.stderr)


def compare(a, b):
    """
    Compare two entities, return match status.
    """
    if len(a.get("title", "")) < 5:
        return (Status.AMBIGUOUS, Miss.SHORT_TITLE)
    if a.get("title", "").lower() in TITLE_BLACKLIST:
        return (Status.AMBIGUOUS, Miss.BLACKLISTED)

    if "Zweckverband Volkshochschule " in a.get("title") and a.get("title") != b.get("title"):
        return (Status.DIFFERENT, Miss.CUSTOM_VHS)

    arxiv_id_a = a.get("ext_ids", {}).get("arxiv")
    arxiv_id_b = b.get("ext_ids", {}).get("arxiv")

    a_authors = set([v.get("raw_name") for v in a.get("contribs", [])])
    b_authors = set([v.get("raw_name") for v in b.get("contribs", [])])
    a_release_year = a.get("release_year")
    b_release_year = b.get("release_year")

    if a.get("title") == b.get("title"):
        if a_authors and (a_authors == b_authors):
            if a_release_year and b_release_year and a_release_year != b_release_year:
                return (Status.DIFFERENT, Miss.YEAR)
            return (Status.EXACT, OK.TITLE_AUTHOR_MATCH)

    a_slug_title = slugify_string(a.get("title"))
    b_slug_title = slugify_string(b.get("title"))

    if a_slug_title and b_slug_title and a_slug_title == b_slug_title:
        if a_authors and len(a_authors & b_authors) > 0:
            if arxiv_id_a is not None and arxiv_id_b is None or arxiv_id_a is None and arxiv_id_b is not None:
                return (Status.STRONG, OK.PREPRINT_PUBLISHED)

    arxiv_id_a = a.get("ext_ids", {}).get("arxiv")
    arxiv_id_b = b.get("ext_ids", {}).get("arxiv")
    if arxiv_id_a and arxiv_id_b:
        id_a, version_a = arxiv_id_a.split("v")
        id_b, version_b = arxiv_id_b.split("v")
        if id_a == id_b:
            return (Status.STRONG, OK.ARXIV_VERSION)
        else:
            return (Status.DIFFERENT, Miss.ARXIV_VERSION)

    if a_authors and len(a_authors & b_authors) == 0:
        return (Status.DIFFERENT, Miss.CONTRIB_INTERSECTION_EMPTY)

    return (Status.AMBIGUOUS, OK.DUMMY)
