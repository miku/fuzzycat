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
import re
import sys
from enum import Enum

from fuzzycat.cluster import slugify_string

get_key_values = operator.itemgetter("k", "v")

# There titles appear too often, so ignore them for now.
TITLE_BLACKLIST = set([
    "",
    ":{unav)",
    "[others]",
    "[s.n.]",
    "a correction",
    "abbildung",
    "abbildungsnachweis",
    "abbreviations and acronyms",
    "about the cover",
    "about the editor",
    "about the editors",
    "about this issue",
    "about this journal",
    "about this title",
    "abréviations",
    "abstracts of papers to appear in future issues",
    "abstracts",
    "acknowledgement of reviewers",
    "acknowledgements to reviewers",
    "acknowledgements",
    "acknowledgment of reviewers",
    "acknowledgments",
    "actualités",
    "agradecimento",
    "announcement",
    "announcements",
    "annual report",
    "around the world",
    "arthrobacter sp.",
    "aufgaben",
    "author index",
    "author response image 1. author response",
    "back matter",
    "backmatter",
    "bibliography",
    "book review",
    "book reviews",
    "books received",
    "bookseller's catalogue",
    "bureau of investigation",
    "calendar",
    "canto",
    "canto",
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
    "editorial board",
    "editorial",
    "einleitung",
    "erratum",
    "foreword",
    "front cover",
    "front matter",
    "frontmatter",
    "fundraising",
    "gbif occurrence download",
    "in this issue",
    "index",
    "inhalt",
    "interlude",
    "introduction",
    "issue information",
    "letter to the editor",
    "letters to the editor",
    "list of delegates",
    "masthead",
    "methotrexate",
    "miscellany",
    "news section",
    "news",
    "not available",
    "note of appreciation / note de reconnaissance",
    "notes",
    "occurrence download",
    "oup accepted manuscript",
    "parliamentary intelligence",
    "petitions.xlsx",
    "positions available",
    "preface",
    "preliminary material",
    "preservation image",
    "references",
    "regulations",
    "reply",
    "reviews of books",
    "reviews",
    "short notices",
    "streptomyces sp.",
    "subject index",
    "table of contents",
    "taxonomic abstract for the species.",
    "the applause data release 2",
    "奥付",
    "投稿規定",
    "目次",
    "表紙",
    "裏表紙",
])

CONTAINER_NAME_BLACKLIST = set([
    "crossref listing of deleted dois",
])

PUBLISHER_BLACKLIST = set([
    "test accounts",
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
    SLUG_TITLE_AUTHOR_MATCH = 'ok.slug_title_author_match'


class Miss(str, Enum):
    """
    Reasons indicating mismatch.
    """
    ARXIV_VERSION = 'miss.arxiv_version'
    BLACKLISTED = 'miss.blacklisted'
    CONTRIB_INTERSECTION_EMPTY = 'miss.contrib_intersection_empty'
    SHORT_TITLE = 'miss.short_title'
    YEAR = 'miss.year'
    CUSTOM_VHS = 'miss.vhs'  # https://fatcat.wiki/release/44gk5ben5vghljq6twm7lwmxla
    NUM_DIFF = 'miss.num_diff'
    DATASET_DOI = 'miss.dataset_doi'

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
                self.counter["skip.unique"] += 1
                continue
            if len(vs) > self.max_cluster_size:
                self.counter["skip.too_large"] += 1
                continue
            for a, b in itertools.combinations(vs, r=2):
                for re in (a, b):
                    if re.get("extra", {}).get("container_name", "").lower().strip() in CONTAINER_NAME_BLACKLIST:
                        self.counter["skip.container_name_blacklist"] += 1
                        continue
                    if re.get("publisher", "").lower().strip() in PUBLISHER_BLACKLIST:
                        self.counter["skip.publisher_blacklist"] += 1
                        continue
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

    if (a.get("extra", {}).get("crossref", {}).get("type",  {}) == "dataset" and
        b.get("extra", {}).get("crossref", {}).get("type",  {}) == "dataset"):
        if (a.get("ext_ids", {}).get("doi") and b.get("ext_ids", {}).get("doi") and
            a.get("ext_ids", {}).get("doi") != b.get("ext_ids", {}).get("doi")):
            return (Status.DIFFERENT, Miss.DATASET_DOI)

    arxiv_id_a = a.get("ext_ids", {}).get("arxiv")
    arxiv_id_b = b.get("ext_ids", {}).get("arxiv")

    a_authors = set([v.get("raw_name") for v in a.get("contribs", [])])
    b_authors = set([v.get("raw_name") for v in b.get("contribs", [])])
    a_slug_authors = set((slugify_string(v) for v in a_authors if v))
    b_slug_authors = set((slugify_string(v) for v in b_authors if v))
    a_release_year = a.get("release_year")
    b_release_year = b.get("release_year")

    if a.get("title", "").lower() == b.get("title", "").lower():
        if a_authors and (a_authors == b_authors):
            if a_release_year and b_release_year and a_release_year != b_release_year:
                return (Status.DIFFERENT, Miss.YEAR)
            return (Status.EXACT, OK.TITLE_AUTHOR_MATCH)

    if a.get("title") and a.get("title") == b.get("title"):
        if a_release_year and b_release_year:
            if abs(int(a_release_year) - int(b_release_year)) > 2:
                return (Status.DIFFERENT, Miss.YEAR)

    # https://fatcat.wiki/release/knzhequchfcethcyyi3gsp5gry, some title contain newlines
    a_slug_title = slugify_string(a.get("title", "")).replace("\n", " ")
    b_slug_title = slugify_string(b.get("title", "")).replace("\n", " ")

    if re.search(r'\d', a_slug_title) and a_slug_title != b_slug_title and num_project(
            a_slug_title) == num_project(b_slug_title):
        return (Status.DIFFERENT, Miss.NUM_DIFF)

    if a_slug_title and b_slug_title and a_slug_title == b_slug_title:
        if a_authors and len(a_authors & b_authors) > 0:
            if arxiv_id_a is not None and arxiv_id_b is None or arxiv_id_a is None and arxiv_id_b is not None:
                return (Status.STRONG, OK.PREPRINT_PUBLISHED)

    if a_slug_title and b_slug_title and a_slug_title.strip().replace(" ", "") == b_slug_title.strip().replace(" ", ""):
        if len(a_slug_authors & b_slug_authors) > 0:
            return (Status.STRONG, OK.SLUG_TITLE_AUTHOR_MATCH)

    arxiv_id_a = a.get("ext_ids", {}).get("arxiv")
    arxiv_id_b = b.get("ext_ids", {}).get("arxiv")
    if arxiv_id_a and arxiv_id_b:
        id_a, version_a = arxiv_id_a.split("v")
        id_b, version_b = arxiv_id_b.split("v")
        if id_a == id_b:
            return (Status.STRONG, OK.ARXIV_VERSION)
        else:
            return (Status.DIFFERENT, Miss.ARXIV_VERSION)

    if a_authors and len(a_slug_authors & b_slug_authors) == 0:
        return (Status.DIFFERENT, Miss.CONTRIB_INTERSECTION_EMPTY)

    return (Status.AMBIGUOUS, OK.DUMMY)


def num_project(s):
    """
    Cf. https://fatcat.wiki/release/6b5yupd7bfcw7gp73hjoavbgfq,
    https://fatcat.wiki/release/7hgzqz3hrngq7omtwdxz4qx34u

    Unify every occurence of a digit (or group of digits).
    """
    return re.sub('\d+', '<NUM>', s)

