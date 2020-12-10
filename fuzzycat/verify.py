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

WIPv1 (10m)

    {
      "miss.appendix": 176,
      "miss.blacklisted": 12124,
      "miss.blacklisted_fragment": 9,
      "miss.book_chapter": 46733,
      "miss.component": 2173,
      "miss.contrib_intersection_empty": 73592,
      "miss.dataset_doi": 30806,
      "miss.num_diff": 1,
      "miss.release_type": 19767,
      "miss.short_title": 16737,
      "miss.subtitle": 11975,
      "miss.title_filename": 87,
      "miss.year": 123288,
      "ok.arxiv_version": 90726,
      "ok.dummy": 106196,
      "ok.preprint_published": 10495,
      "ok.slug_title_author_match": 47285,
      "ok.title_author_match": 65685,
      "ok.tokenized_authors": 7592,
      "skip.container_name_blacklist": 20,
      "skip.publisher_blacklist": 456,
      "skip.too_large": 7430,
      "skip.unique": 8808462,
      "total": 9481815
    }


TODO: allow to pass in a DOI blacklist, e.g. a list of DOI which are not valid
any more; example: https://fatcat.wiki/release/azbcyqjnmrdofigpgk24ck4rpq,
https://fatcat.wiki/release/eb2uf5ae7bedxe22jasf2l3faa

Author matching: one long string; e.g. as last name; take an acronym of the
first name; asian names; number of authors; what works specifically for the
various md extractors

Contributor lists; "one that have the index set"; affiliations may end up
there; "subset" is an ordered list; pubmed, crossref important
"""

import collections
import itertools
import json
import operator
import re
import sys

from glom import PathAccessError, glom

from fuzzycat.common import OK, Miss, Status
from fuzzycat.data import (CONTAINER_NAME_BLACKLIST, PUBLISHER_BLACKLIST, TITLE_BLACKLIST,
                           TITLE_FRAGMENT_BLACKLIST)
from fuzzycat.utils import (author_similarity_score, contains_chemical_formula, has_doi_prefix,
                            jaccard, num_project, slugify_string)

# The result of clustering are documents that have a key k and a list of values
# (of the cluster) v.
get_key_values = operator.itemgetter("k", "v")


class GroupVerifier:
    """
    Verifier.

    Within a group, we could have multiple sub clusters, e.g.

    > [AABAB]

    We would need to compare each possible pair and decide whether they are the
    same.
    """
    def __init__(self,
                 iterable: collections.abc.Iterable,
                 max_cluster_size: int = 10,
                 verbose=True):
        self.iterable: collections.abc.Iterable = iterable
        self.max_cluster_size: int = max_cluster_size
        self.verbose = verbose
        self.counter = collections.Counter()

    def run(self):
        for i, line in enumerate(self.iterable):
            if i % 20000 == 0 and self.verbose:
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
                    container_name = re.get("extra", {}).get("container_name", "") or ""
                    if container_name.lower().strip() in CONTAINER_NAME_BLACKLIST:
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


def dict_key_exists(doc, path):
    """
    Return true, if a value at a given path exists. XXX: probably in glom, too.
    """
    try:
        _ = glom(doc, path)
    except PathAccessError:
        return False
    else:
        return True


def compare(a, b):
    """
    Compare two entities, return match status and reason.

    TODO: We might want a bunch of kwargs for things like year gap threshold
    and the like.
    """
    try:
        if glom(a, "ext_ids.doi") == glom(b, "ext_ids.doi"):
            return (Status.EXACT, OK.DOI)
    except PathAccessError:
        pass

    if a.get("work_id") and a.get("work_id") == b.get("work_id"):
        return (Status.EXACT, OK.WORK_ID)

    a_title = a.get("title", "")
    a_title_lower = a_title.lower()
    b_title = b.get("title", "")
    b_title_lower = b_title.lower()

    if len(a_title) < 5:
        return (Status.AMBIGUOUS, Miss.SHORT_TITLE)
    if a_title_lower in TITLE_BLACKLIST:
        return (Status.AMBIGUOUS, Miss.BLACKLISTED)

    for fragment in TITLE_FRAGMENT_BLACKLIST:
        if fragment in a_title_lower:
            return (Status.AMBIGUOUS, Miss.BLACKLISTED_FRAGMENT)

    # https://fatcat.wiki/release/rnso2swxzvfonemgzrth3arumi,
    # https://fatcat.wiki/release/caxa7qbfqvg3bkgz4nwvapgnvi
    if "subject index" in a_title_lower and "subject index" in b_title_lower:
        try:
            if glom(a, "container_id") != glom(b, "container_id"):
                return (Status.DIFFERENT, Miss.CONTAINER)
        except PathAccessError:
            pass

    try:
        if a_title and a_title == b_title and glom(a, "extra.datacite.metadataVersion") != glom(
                b, "extra.datacite.metadataVersion"):
            return (Status.EXACT, OK.DATACITE_VERSION)
    except PathAccessError:
        pass

    try:
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        if a_doi.startswith("10.14288/") and b_doi.startswith("10.14288/") and a_doi != b_doi:
            # UBC metadata slightly off;
            # https://fatcat.wiki/release/63g4ukdxajcqhdytqla6du3t3u,
            # https://fatcat.wiki/release/rz72bzfevzeofdeb342c6z45qu;
            # https://api.datacite.org/application/vnd.datacite.datacite+json/10.14288/1.0011045
            return (Status.DIFFERENT, Miss.CUSTOM_PREFIX_10_14288)
    except PathAccessError:
        pass

    try:
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        if has_doi_prefix(a_doi, "10.3403") and has_doi_prefix(b_doi, "10.3403"):
            if a_doi + "u" == b_doi or b_doi + "u" == a_doi:
                return (Status.STRONG, OK.CUSTOM_BSI_UNDATED)
            # Reference to subdocument.
            # https://api.fatcat.wiki/v0/release/tcro5wr6brhqnf5wettyiauw34
            # https://api.fatcat.wiki/v0/release/s7a4o5v5gfg4tbzna6poyg7nzy
            if a_title == b_title and ((dict_key_exists(a, "extra.subtitle")
                                        and not dict_key_exists(b, "extra.subtitle")) or
                                       (dict_key_exists(b, "extra.subtitle")
                                        and not dict_key_exists(a, "extra.subtitle"))):
                return (Status.STRONG, OK.CUSTOM_BSI_SUBDOC)
    except PathAccessError:
        pass

    try:
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        if has_doi_prefix(a_doi, "10.1149") and has_doi_prefix(b_doi, "10.1149"):
            if (a_doi.startswith("10.1149/ma") and not b_doi.startswith("10.1149/ma")
                    or b_doi.startswith("10.1149/ma") and not a_doi.startswith("10.1149/ma")):
                return (Status.DIFFERENT, Miss.CUSTOM_IOP_MA_PATTERN)
    except PathAccessError:
        pass

    if "Zweckverband Volkshochschule " in a_title and a_title != b_title:
        return (Status.DIFFERENT, Miss.CUSTOM_VHS)

    if re.match(r"appendix ?[^ ]*$", a_title_lower):
        return (Status.AMBIGUOUS, Miss.APPENDIX)

    try:
        # TODO: figshare versions, "xxx.v1"
        FIGSHARE_PREFIX = "10.6084/"
        if glom(a, "ext_ids.doi").startswith(FIGSHARE_PREFIX) and glom(
                b, "ext_ids.doi").startswith(FIGSHARE_PREFIX):
            a_doi_v_stripped = re.sub(r"[.]v[0-9]+$", "", glom(a, "ext_ids.doi"))
            b_doi_v_stripped = re.sub(r"[.]v[0-9]+$", "", glom(b, "ext_ids.doi"))
            if a_doi_v_stripped == b_doi_v_stripped:
                return (Status.STRONG, OK.FIGSHARE_VERSION)
    except PathAccessError:
        pass

    try:
        # https://fatcat.wiki/release/cwqujxztefdghhssb7ysxj7b5m
        # https://fatcat.wiki/release/hwnqyz7n65eabhlivvkipkytji
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        versioned_doi_pattern = '10[.].*/v[0-9]{1,}$'
        if re.match(versioned_doi_pattern, a_doi) and re.match(versioned_doi_pattern, b_doi):
            return (Status.STRONG, OK.VERSIONED_DOI)
    except PathAccessError:
        pass

    # TODO: datacite specific vocabulary
    # extra.datacite.relations[].{relationType=IsNewerVersionOf,relatedIdentifier=10...}
    # beware: we have versions and "isPartOf", e.g. https://api.fatcat.wiki/v0/release/ybxygpeypbaq5pfrztu3z2itw4
    # TODO: does glom help?
    # ...
    if "datacite" in (a.get("extra", []) or []) and "datacite" in (b.get("extra", []) or []):
        whitelist = set([
            "HasPart",
            "HasVersion",
            "IsNewVersionOf",
            "IsPartOf",
            "IsPreviousVersionOf",
            "IsVersionOf",
        ])

        def get_datacite_related_doi(doc):
            spec = ("extra.datacite.relations", [{
                "type": "relatedIdentifierType",
                "id": "relatedIdentifier"
            }])
            try:
                return set([v["id"] for v in glom(doc, spec) if v["type"].lower() == "doi"])
            except PathAccessError:
                return set()

        a_doi_rel = get_datacite_related_doi(a)
        b_doi_rel = get_datacite_related_doi(b)
        try:
            if glom(b, "ext_ids.doi") in a_doi_rel or glom(a, "ext_ids.doi") in b_doi_rel:
                return (Status.STRONG, OK.DATACITE_RELATED_ID)
        except PathAccessError:
            pass

    try:
        id_a = re.match(r"(.*)v[0-9]{1,}$", glom(a, "ext_ids.arxiv")).group(1)
        id_b = re.match(r"(.*)v[0-9]{1,}$", glom(b, "ext_ids.arxiv")).group(1)
        if id_a == id_b:
            return (Status.STRONG, OK.ARXIV_VERSION)
    except (AttributeError, ValueError, PathAccessError) as exc:
        pass

    try:
        if glom(a, "release_type") != glom(b, "release_type"):
            # TODO(martin): This can go wrong with "article" and "article-journal"
            # TODO(martin): Some arxiv articles are marked are release_type: report
            # or paper-conference
            # (https://fatcat.wiki/release/l4fyyvsckneuxkq7d3y2zvkvbe)
            types = set([a.get("release_type"), b.get("release_type")])
            # Added "entry" via
            # https://fatcat.wiki/release/xp3oxb7tqbgaxdzkzbchfkcjn4,
            # https://fatcat.wiki/release/73pcaauzwbalvi7aqhv6vopxl4
            ignore_release_types = set([
                "article",
                "article-journal",
                "report",
                "paper-conference",
            ])
            if len(types & ignore_release_types) == 0:
                return (Status.DIFFERENT, Miss.RELEASE_TYPE)
            if "dataset" in types and ("article" in types or "article-journal" in types):
                return (Status.DIFFERENT, Miss.RELEASE_TYPE)
            if "book" in types and ("article" in types or "article-journal" in types):
                return (Status.DIFFERENT, Miss.RELEASE_TYPE)
    except PathAccessError:
        pass

    try:
        if (glom(a, "release_type") == "dataset" and glom(b, "release_type") == "dataset"
                and glom(a, "ext_ids.doi") != glom(b, "ext_ids.doi")):
            return (Status.DIFFERENT, Miss.DATASET_DOI)
    except PathAccessError:
        pass

    try:
        if (glom(a, "release_type") == "chapter" and glom(b, "release_type") == "chapter"
                and glom(a, "extra.container_name") != glom(b, "extra.container_name")):
            return (Status.DIFFERENT, Miss.BOOK_CHAPTER)
    except PathAccessError:
        pass

    try:
        if glom(a, "extra.crossref.type") == "component" and glom(a, "title") != glom(b, "title"):
            return (Status.DIFFERENT, Miss.COMPONENT)
    except PathAccessError:
        pass

    try:
        if glom(a, "release_type") == "component" and glom(b, "release_type") == "component":
            a_doi = glom(a, "ext_ids.doi")
            b_doi = glom(b, "ext_ids.doi")
            if a_doi != b_doi:
                return (Status.DIFFERENT, Miss.COMPONENT)
    except PathAccessError:
        pass

    # https://fatcat.wiki/release/knzhequchfcethcyyi3gsp5gry, some title contain newlines
    a_slug_title = slugify_string(a.get("title", "")).replace("\n", " ")
    b_slug_title = slugify_string(b.get("title", "")).replace("\n", " ")

    # https://fatcat.wiki/release/psykbwxylndtdaand2ymtkgzqu
    # https://fatcat.wiki/release/xizkwvsodzajnn4u7lgeldqoum
    if a_slug_title == b_slug_title:
        a_year = a.get("release_year")
        b_year = b.get("release_year")
        if a_year and b_year and abs(a_year - b_year) > 40:
            return (Status.DIFFERENT, Miss.YEAR)

    if a_slug_title == b_slug_title:
        # via: https://fatcat.wiki/release/ij3yuoh6lrh3tkrv5o7gfk6yyi
        # https://fatcat.wiki/release/tur236mqljdfdnlzbbnks2sily
        def ieee_arxiv_pair_check(a, b):
            try:
                if (glom(a, "ext_ids.doi").split("/")[0] == "10.1109"
                        and glom(b, "ext_ids.arxiv") != ""):
                    return (Status.STRONG, OK.CUSTOM_IEEE_ARXIV)
            except PathAccessError:
                pass

        # TODO: we might want to have some light python DSL to express these
        # (commute) things
        result = ieee_arxiv_pair_check(a, b)
        if result:
            return result
        result = ieee_arxiv_pair_check(b, a)
        if result:
            return result

    if a_slug_title == b_slug_title:
        try:
            # https://dlc.library.columbia.edu/lcaaj/cul:p5hqbzkhxb,
            # https://dlc.library.columbia.edu/lcaaj/cul:5tb2rbp0nj
            a_doi = glom(a, "ext_ids.doi")
            b_doi = glom(b, "ext_ids.doi")
            if has_doi_prefix(a_doi, "10.7916") and has_doi_prefix(b_doi, "10.7916"):
                return (Status.AMBIGUOUS, Miss.CUSTOM_PREFIX_10_7916)
        except PathAccessError:
            pass

    if a_slug_title == b_slug_title:
        try:
            a_subtitles = glom(a, "extra.subtitle") or []
            b_subtitles = glom(b, "extra.subtitle") or []
            for a_sub in a_subtitles:
                for b_sub in b_subtitles:
                    if slugify_string(a_sub) != slugify_string(b_sub):
                        return (Status.DIFFERENT, Miss.SUBTITLE)
        except PathAccessError:
            pass

    arxiv_id_a = a.get("ext_ids", {}).get("arxiv")
    arxiv_id_b = b.get("ext_ids", {}).get("arxiv")

    a_authors = set([v.get("raw_name") for v in a.get("contribs", [])])
    b_authors = set([v.get("raw_name") for v in b.get("contribs", [])])
    a_slug_authors = set((slugify_string(v) for v in a_authors if v))
    b_slug_authors = set((slugify_string(v) for v in b_authors if v))
    a_release_year = a.get("release_year")
    b_release_year = b.get("release_year")

    if a_title_lower == b_title_lower:
        if a_authors and (a_authors == b_authors):
            # TODO: https://fatcat.wiki/release/utx5r5e6azbvljipznv7ejqzvq,
            # https://fatcat.wiki/release/oceozrqtcbc4tloizhddxaj2ti
            # preprint and published work may not be published in the same
            # year; compromise allow a small gap
            if a_release_year and b_release_year and abs(int(a_release_year) -
                                                         int(b_release_year)) > 1:
                return (Status.DIFFERENT, Miss.YEAR)
            return (Status.EXACT, OK.TITLE_AUTHOR_MATCH)

    if (len(a.get("title", "").split()) == 1 and re.match(r".*[.][a-z]{2,3}", a.get("title", ""))
            or len(b.get("title", "").split()) == 1
            and re.match(r".*[.][a-z]{2,3}$", b.get("title", ""))):
        if a.get("title") != b.get("title"):
            return (Status.DIFFERENT, Miss.TITLE_FILENAME)

    if a.get("title") and a.get("title") == b.get("title"):
        if a_release_year and b_release_year:
            if abs(int(a_release_year) - int(b_release_year)) > 2:
                return (Status.DIFFERENT, Miss.YEAR)

    if contains_chemical_formula(a_slug_title) or contains_chemical_formula(b_slug_title) and (
            a_slug_title != b_slug_title):
        return (Status.DIFFERENT, Miss.CHEM_FORMULA)

    if len(a_slug_title) < 10 and a_slug_title != b_slug_title:
        return (Status.AMBIGUOUS, Miss.SHORT_TITLE)

    if re.search(r'\d+', a_slug_title) and a_slug_title != b_slug_title and num_project(
            a_slug_title) == num_project(b_slug_title):
        return (Status.DIFFERENT, Miss.NUM_DIFF)

    if a_slug_title and b_slug_title and a_slug_title == b_slug_title:
        if a_authors and len(a_authors & b_authors) > 0:
            if arxiv_id_a is not None and arxiv_id_b is None or arxiv_id_a is None and arxiv_id_b is not None:
                return (Status.STRONG, OK.PREPRINT_PUBLISHED)

    if a_slug_title and b_slug_title and a_slug_title.strip().replace(
            " ", "") == b_slug_title.strip().replace(" ", ""):
        if len(a_slug_authors & b_slug_authors) > 0:
            return (Status.STRONG, OK.SLUG_TITLE_AUTHOR_MATCH)

    # if any([a_authors, b_authors]) and not (a_authors and b_authors):
    # Does not cover case, where both authors are empty.
    if a_release_year == b_release_year and a_title_lower == b_title_lower:
        if ((dict_key_exists(a, "ext_ids.pmid") and dict_key_exists(b, "ext_ids.doi"))
                or (dict_key_exists(b, "ext_ids.pmid") and dict_key_exists(a, "ext_ids.doi"))):
            return (Status.STRONG, OK.PMID_DOI_PAIR)

    # Two JSTOR items will probably be different.
    try:
        a_jstor_id = glom(a, "ext_ids.jstor")
        b_jstor_id = glom(b, "ext_ids.jstor")
        if a_jstor_id != b_jstor_id:
            return (Status.DIFFERENT, Miss.JSTOR_ID)
    except PathAccessError:
        pass

    # Publication from same publisher and different DOI or year a probably
    # different.
    try:
        a_container_id = glom(a, "container_id")
        b_container_id = glom(b, "container_id")
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")

        if a_container_id == b_container_id and a_doi != b_doi and not has_doi_prefix(
                a_doi, "10.1126"):
            return (Status.DIFFERENT, Miss.SHARED_DOI_PREFIX)
    except PathAccessError:
        pass

    if a_authors and len(a_slug_authors & b_slug_authors) == 0:
        # Before we bail out, run an authors similarity check. TODO: This is
        # not the right place, but lives here now, since these cases popped up
        # in this block.
        Score = collections.namedtuple("Score", "a b value")
        scores = []
        # account for the possible arbitrary ordering of authors, XXX: this
        # explodes.
        a_trimmed = sorted(a_slug_authors)[:5]
        b_trimmed = sorted(b_slug_authors)[:5]
        for a, b in itertools.product(a_trimmed, b_trimmed):
            scores.append(Score(a, b, author_similarity_score(a, b)))
        # TODO: less arbitrary metric and threshold
        top_scores = []
        for _, g in itertools.groupby(scores, key=lambda s: s.a):
            sorted_scores = sorted(g, key=lambda s: s.value, reverse=True)
            if len(sorted_scores) > 0:
                top_scores.append(sorted_scores[0].value)
        if len(top_scores) > 0:
            avg_score = sum(top_scores) / len(top_scores)
            if avg_score > 0.5:
                return (Status.STRONG, OK.TOKENIZED_AUTHORS)
            else:
                pass
                # Kuidong Xu, Joong Ki Choi, Eun Jin Yang, Kyu Chul Lee, Yanli Lei
                # J.K. Choi, K. Xu, E.J. Yang, K.C. Lee, Y. Lei
                # 0.2942857142857143
                # print("author comp score: {}".format(avg_score))

        # Fallback jaccard token comparison.
        # Kuidong Xu, Joong Ki Choi, Eun Jin Yang, Kyu Chul Lee, Yanli Lei
        # J.K. Choi, K. Xu, E.J. Yang, K.C. Lee, Y. Lei
        # avg_score was 0.2942857142857143, but jaccard ~0.38
        a_tok = [tok for tok in re.findall(r"[\w]{3,}", " ".join(a_slug_authors)) if tok]
        b_tok = [tok for tok in re.findall(r"[\w]{3,}", " ".join(b_slug_authors)) if tok]
        if jaccard(set(a_tok), set(b_tok)) > 0.35:
            return (Status.STRONG, OK.JACCARD_AUTHORS)

        # TODO: This misses spelling differences, e.g.
        # https://fatcat.wiki/release/7nbcgsohrrak5cuyk6dnit6ega and
        # https://fatcat.wiki/release/q66xv7drk5fnph7enwwlkyuwqm
        return (Status.DIFFERENT, Miss.CONTRIB_INTERSECTION_EMPTY)

    # mark choicereview articles as ambiguous, as they seem to be behind a paywall
    try:
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        if has_doi_prefix(a_doi, "10.5860") or has_doi_prefix(b_doi, "10.5860"):
            return (Status.AMBIGUOUS, Miss.CUSTOM_PREFIX_10_5860_CHOICE_REVIEW)
    except PathAccessError:
        pass

    # If pages exists, but differ too much, bail out.
    # https://fatcat.wiki/release/tm3gaiumkvb3xc7t3i6suna6u4
    # https://fatcat.wiki/release/r6dj63wh3zcrrolisn6xuacnve
    try:
        a_pages = glom(a, "pages")
        b_pages = glom(b, "pages")
        page_pattern = re.compile("([0-9]{1,})-([0-9]{1,})")
        a_match = page_pattern.match(a_pages)
        b_match = page_pattern.match(b_pages)
        if a_match and b_match:
            a_start, a_end = a_match.groups()
            b_start, b_end = b_match.groups()
            a_num_pages = int(a_end) - int(a_start)
            b_num_pages = int(b_end) - int(b_start)
            if a_num_pages >= 0 and b_num_pages >= 0:
                if abs(a_num_pages - b_num_pages) > 5:
                    return (Status.DIFFERENT, Miss.PAGE_COUNT)
    except PathAccessError:
        pass

    return (Status.AMBIGUOUS, OK.DUMMY)
