"""
Verification part of matching.

Clustering results in a documents with keys and values, where values is a list
of entites associated with a cluster.

    {
      "v": [
        {...}, ...
      ],
      "k": "1 Grundlagen",
    }

The list of documents will often contain false positives. The `verify` routine
is a way to get a match quality assessment.

> Notes

TODO: allow to pass in a DOI blacklist, e.g. a list of DOI which are not valid
any more; example: https://fatcat.wiki/release/azbcyqjnmrdofigpgk24ck4rpq,
https://fatcat.wiki/release/eb2uf5ae7bedxe22jasf2l3faa

Author matching: one long string; e.g. as last name; take an acronym of the
first name; asian names; number of authors; what works specifically for the
various md extractors

Contributor lists; "one that have the index set"; affiliations may end up
there; "subset" is an ordered list; pubmed, crossref important

> Stats

Stats from running over a full database dump. We need to run verification over
25586837 entity pairs, of which we 1346217/25586837 (or about 5%) are too
ambiguous at this time.

Found   Status                  Reason
--------------------------------------------------------------------------
3450874 Status.EXACT    	Reason.TITLE_AUTHOR_MATCH
2619990 Status.STRONG   	Reason.SLUG_TITLE_AUTHOR_MATCH
2487633 Status.DIFFERENT        Reason.YEAR
2434532 Status.EXACT    	Reason.WORK_ID
2085006 Status.DIFFERENT        Reason.CONTRIB_INTERSECTION_EMPTY
1397420 Status.DIFFERENT        Reason.SHARED_DOI_PREFIX
1355852 Status.DIFFERENT        Reason.RELEASE_TYPE
1290162 Status.AMBIGUOUS        Reason.UNKNOWN
1145511 Status.DIFFERENT        Reason.BOOK_CHAPTER
1009657 Status.DIFFERENT        Reason.DATASET_DOI
 996503 Status.STRONG   	Reason.PMID_DOI_PAIR
 868951 Status.EXACT    	Reason.DATACITE_VERSION
 796216 Status.STRONG   	Reason.DATACITE_RELATED_ID
 704154 Status.STRONG   	Reason.FIGSHARE_VERSION
 534963 Status.STRONG   	Reason.VERSIONED_DOI
 343310 Status.STRONG   	Reason.TOKENIZED_AUTHORS
 334974 Status.STRONG   	Reason.JACCARD_AUTHORS
 293835 Status.STRONG   	Reason.PREPRINT_PUBLISHED
 269366 Status.DIFFERENT        Reason.COMPONENT
 263626 Status.DIFFERENT        Reason.SUBTITLE
 224021 Status.AMBIGUOUS        Reason.SHORT_TITLE
 152990 Status.DIFFERENT        Reason.PAGE_COUNT
 133811 Status.AMBIGUOUS        Reason.CUSTOM_PREFIX_10_5860_CHOICE_REVIEW
 122600 Status.AMBIGUOUS        Reason.CUSTOM_PREFIX_10_7916
  79664 Status.STRONG   	Reason.CUSTOM_IEEE_ARXIV
  46649 Status.DIFFERENT        Reason.CUSTOM_PREFIX_10_14288
  39797 Status.DIFFERENT        Reason.JSTOR_ID
  38598 Status.STRONG   	Reason.CUSTOM_BSI_UNDATED
  18907 Status.STRONG   	Reason.CUSTOM_BSI_SUBDOC
  15465 Status.EXACT    	Reason.DOI
  13393 Status.DIFFERENT        Reason.CUSTOM_IOP_MA_PATTERN
  10378 Status.DIFFERENT        Reason.CONTAINER
   3081 Status.AMBIGUOUS        Reason.BLACKLISTED
   2504 Status.AMBIGUOUS        Reason.BLACKLISTED_FRAGMENT
   1273 Status.AMBIGUOUS        Reason.APPENDIX
   1063 Status.DIFFERENT        Reason.TITLE_FILENAME
    104 Status.DIFFERENT        Reason.NUM_DIFF
      4 Status.STRONG   	Reason.ARXIV_VERSION
"""

import collections
import itertools
import json
import operator
import re
import sys
from typing import Counter, Dict, Tuple, Type

from fatcat_openapi_client import ReleaseEntity
from glom import PathAccessError, glom

from fuzzycat.common import Reason, Status
from fuzzycat.data import (CONTAINER_NAME_BLACKLIST, PUBLISHER_BLACKLIST, TITLE_BLACKLIST,
                           TITLE_FRAGMENT_BLACKLIST)
from fuzzycat.entities import entity_to_dict
from fuzzycat.utils import (author_similarity_score, contains_chemical_formula, dict_key_exists,
                            doi_prefix, has_doi_prefix, jaccard, num_project, parse_page_string,
                            slugify_string)

Verify = collections.namedtuple("Verify", "status reason")


class GroupVerifier:
    """
    Given an iterable (lines) from clustering step, run verification on every
    pair of the cluster, e.g. a cluster of four elements will yield nCr(4, 2) =
    10 pairs.
    """
    def __init__(self,
                 iterable: collections.abc.Iterable,
                 max_cluster_size: int = 10,
                 verbose=False):
        self.iterable: collections.abc.Iterable = iterable
        self.max_cluster_size: int = max_cluster_size
        self.verbose: bool = verbose
        self.counter: Counter = collections.Counter()

    def run(self):
        # The result of clustering are documents that have a key k and a list of values
        # (of the cluster) v.
        get_key_values = operator.itemgetter("k", "v")
        for i, line in enumerate(self.iterable):
            if i % 20000 == 0 and self.verbose:
                print(i, file=sys.stderr)
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            k, vs = get_key_values(doc)
            if len(vs) < 2:
                self.counter[Reason.SINGULAR_CLUSTER] += 1
                continue
            if len(vs) > self.max_cluster_size:
                self.counter[Reason.MAX_CLUSTER_SIZE_EXCEEDED] += 1
                continue
            for a, b in itertools.combinations(vs, r=2):
                for re in (a, b):
                    container_name = re.get("extra", {}).get("container_name", "") or ""
                    if container_name.lower().strip() in CONTAINER_NAME_BLACKLIST:
                        self.counter[Reason.CONTAINER_NAME_BLACKLIST] += 1
                        continue
                    if re.get("publisher", "").lower().strip() in PUBLISHER_BLACKLIST:
                        self.counter[Reason.PUBLISHER_BLACKLIST] += 1
                        continue
                result, reason = verify(a, b)
                self.counter[reason] += 1
                print("https://fatcat.wiki/release/{}".format(a["ident"]),
                      "https://fatcat.wiki/release/{}".format(b["ident"]), result, reason)

        self.counter["total"] = sum(v for _, v in self.counter.items())


def verify_release_entities(a: ReleaseEntity, b: ReleaseEntity, min_title_length=5) -> Type[Verify]:
    return verify(entity_to_dict(a), entity_to_dict(b), min_title_length=min_title_length)


def verify(a: Dict, b: Dict, min_title_length=5) -> Tuple[str, str]:
    """
    Compare two entities (dicts), return tuple of match status and reason.

    Note: This is a too long function, but tested so open to near-term
    refactor. On the plus, it is uniform in the sense, that a few lines take
    care of a specific case.

    The cases are relatively independent, so order should not matter, but that
    can be pinned down much more clearly.

    TODO: add wrapper release entities
    """

    # A few items have the same DOI.
    try:
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        if a_doi is not None and a_doi == b_doi:
            return Verify(Status.EXACT, Reason.DOI)
    except PathAccessError:
        pass

    # Some pre-verified pairs.
    if a.get("work_id") and a.get("work_id") == b.get("work_id"):
        return Verify(Status.EXACT, Reason.WORK_ID)

    a_title = a.get("title", "") or ""
    a_title_lower = a_title.lower()
    b_title = b.get("title", "") or ""
    b_title_lower = b_title.lower()

    if len(a_title) < min_title_length:
        return Verify(Status.AMBIGUOUS, Reason.SHORT_TITLE)
    if a_title_lower in TITLE_BLACKLIST:
        return Verify(Status.AMBIGUOUS, Reason.BLACKLISTED)
    for fragment in TITLE_FRAGMENT_BLACKLIST:
        if fragment in a_title_lower:
            return Verify(Status.AMBIGUOUS, Reason.BLACKLISTED_FRAGMENT)

    # https://fatcat.wiki/release/rnso2swxzvfonemgzrth3arumi,
    # https://fatcat.wiki/release/caxa7qbfqvg3bkgz4nwvapgnvi
    if "subject index" in a_title_lower and "subject index" in b_title_lower:
        try:
            if glom(a, "container_id") != glom(b, "container_id"):
                return Verify(Status.DIFFERENT, Reason.CONTAINER)
        except PathAccessError:
            pass

    # Datacite keeps track of versions.
    try:
        if a_title and a_title == b_title and glom(a, "extra.datacite.metadataVersion") != glom(
                b, "extra.datacite.metadataVersion"):
            return Verify(Status.EXACT, Reason.DATACITE_VERSION)
    except PathAccessError:
        pass

    # UBC repository, we assume that different items in the same pool.
    try:
        prefix = "10.14288/"
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        if a_doi.startswith(prefix) and b_doi.startswith(prefix) and a_doi != b_doi:
            # UBC metadata slightly off;
            # https://fatcat.wiki/release/63g4ukdxajcqhdytqla6du3t3u,
            # https://fatcat.wiki/release/rz72bzfevzeofdeb342c6z45qu;
            # https://api.datacite.org/application/vnd.datacite.datacite+json/10.14288/1.0011045
            return Verify(Status.DIFFERENT, Reason.CUSTOM_PREFIX_10_14288)
    except PathAccessError:
        pass

    # The British Standards Institution (BSI) keeps various version of
    # standards around, among them an "undated" variant.
    # Reference to subdocument.
    # https://api.fatcat.wiki/v0/release/tcro5wr6brhqnf5wettyiauw34
    # https://api.fatcat.wiki/v0/release/s7a4o5v5gfg4tbzna6poyg7nzy
    try:
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        if has_doi_prefix(a_doi, "10.3403") and has_doi_prefix(b_doi, "10.3403"):
            if a_doi + "u" == b_doi or b_doi + "u" == a_doi:
                return Verify(Status.STRONG, Reason.CUSTOM_BSI_UNDATED)
            if a_title == b_title and ((dict_key_exists(a, "extra.subtitle")
                                        and not dict_key_exists(b, "extra.subtitle")) or
                                       (dict_key_exists(b, "extra.subtitle")
                                        and not dict_key_exists(a, "extra.subtitle"))):
                return Verify(Status.STRONG, Reason.CUSTOM_BSI_SUBDOC)
    except PathAccessError:
        pass

    # IOP science.
    try:
        prefix = "10.1149"
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        if has_doi_prefix(a_doi, prefix) and has_doi_prefix(b_doi, prefix):
            v = "{}/ma".format(prefix)
            if (a_doi.startswith(v) and not b_doi.startswith(v)
                    or b_doi.startswith(v) and not a_doi.startswith(v)):
                return Verify(Status.DIFFERENT, Reason.CUSTOM_IOP_MA_PATTERN)
    except PathAccessError:
        pass

    # Very manual, XXX: move this into blacklist.
    if "Zweckverband Volkshochschule " in a_title and a_title != b_title:
        return Verify(Status.DIFFERENT, Reason.CUSTOM_VHS)

    if re.match(r"appendix ?[^ ]*$", a_title_lower):
        return Verify(Status.AMBIGUOUS, Reason.APPENDIX)

    # Figshare, versions.
    try:
        FIGSHARE_PREFIX = "10.6084/"
        if glom(a, "ext_ids.doi").startswith(FIGSHARE_PREFIX) and glom(
                b, "ext_ids.doi").startswith(FIGSHARE_PREFIX):
            a_doi_v_stripped = re.sub(r"[.]v[0-9]+$", "", glom(a, "ext_ids.doi"))
            b_doi_v_stripped = re.sub(r"[.]v[0-9]+$", "", glom(b, "ext_ids.doi"))
            if a_doi_v_stripped == b_doi_v_stripped:
                return Verify(Status.STRONG, Reason.FIGSHARE_VERSION)
    except PathAccessError:
        pass

    # Generic, versioned DOI.
    # https://fatcat.wiki/release/cwqujxztefdghhssb7ysxj7b5m
    # https://fatcat.wiki/release/hwnqyz7n65eabhlivvkipkytji
    try:
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        versioned_doi_pattern = '10[.].*/v[0-9]{1,}$'
        if re.match(versioned_doi_pattern, a_doi) and re.match(versioned_doi_pattern, b_doi):
            return Verify(Status.STRONG, Reason.VERSIONED_DOI)
    except PathAccessError:
        pass

    # A paper/component pattern.  10.1021/acs.cgd.7b00396,
    # https://fatcat.wiki/release/c43itb7esjc3heb64xbohigqge,
    # https://fatcat.wiki/release/6kuxfopbcjcrdnhvfokjgbd5wm
    try:
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        if a_doi.split(".")[:-1] == b_doi.split(".") or a_doi.split(".") == b_doi.split(".")[:-1]:
            return Verify(Status.STRONG, Reason.VERSIONED_DOI)
    except PathAccessError:
        pass

    # Datacite related identifiers.
    # extra.datacite.relations[].{relationType=IsNewerVersionOf,relatedIdentifier=10...}
    # beware: we have versions and "isPartOf", e.g.
    # https://api.fatcat.wiki/v0/release/ybxygpeypbaq5pfrztu3z2itw4
    # Datacite md schema: https://doi.org/10.14454/7xq3-zf69
    if dict_key_exists(a, "extra.datacite") and dict_key_exists(b, "extra.datacite"):
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
                return Verify(Status.STRONG, Reason.DATACITE_RELATED_ID)
        except PathAccessError:
            pass

    # Arxiv versions.
    try:
        id_a = re.match(r"(.*)v[0-9]{1,}$", glom(a, "ext_ids.arxiv")).group(1)
        id_b = re.match(r"(.*)v[0-9]{1,}$", glom(b, "ext_ids.arxiv")).group(1)
        if id_a == id_b:
            return Verify(Status.STRONG, Reason.ARXIV_VERSION)
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
                return Verify(Status.DIFFERENT, Reason.RELEASE_TYPE)
            if "dataset" in types and ("article" in types or "article-journal" in types):
                return Verify(Status.DIFFERENT, Reason.RELEASE_TYPE)
            if "book" in types and ("article" in types or "article-journal" in types):
                return Verify(Status.DIFFERENT, Reason.RELEASE_TYPE)
    except PathAccessError:
        pass

    # Datasets are typically different (and have less md and look similar).
    try:
        if (glom(a, "release_type") == "dataset" and glom(b, "release_type") == "dataset"
                and glom(a, "ext_ids.doi") != glom(b, "ext_ids.doi")):
            return Verify(Status.DIFFERENT, Reason.DATASET_DOI)
    except PathAccessError:
        pass

    # Common chapter names should be handled here.
    try:
        if (glom(a, "release_type") == "chapter" and glom(b, "release_type") == "chapter"
                and glom(a, "extra.container_name") != glom(b, "extra.container_name")):
            return Verify(Status.DIFFERENT, Reason.BOOK_CHAPTER)
    except PathAccessError:
        pass

    # Components tend to have similar names.
    try:
        if glom(a, "extra.crossref.type") == "component" and glom(a, "title") != glom(b, "title"):
            return Verify(Status.DIFFERENT, Reason.COMPONENT)
    except PathAccessError:
        pass

    try:
        if glom(a, "release_type") == "component" and glom(b, "release_type") == "component":
            a_doi = glom(a, "ext_ids.doi")
            b_doi = glom(b, "ext_ids.doi")
            if a_doi != b_doi:
                return Verify(Status.DIFFERENT, Reason.COMPONENT)
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
            return Verify(Status.DIFFERENT, Reason.YEAR)

    if a_slug_title == b_slug_title:
        # via: https://fatcat.wiki/release/ij3yuoh6lrh3tkrv5o7gfk6yyi
        # https://fatcat.wiki/release/tur236mqljdfdnlzbbnks2sily
        def ieee_arxiv_pair_check(a, b):
            try:
                if (glom(a, "ext_ids.doi").split("/")[0] == "10.1109"
                        and glom(b, "ext_ids.arxiv") != ""):
                    return Verify(Status.STRONG, Reason.CUSTOM_IEEE_ARXIV)
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
                return Verify(Status.AMBIGUOUS, Reason.CUSTOM_PREFIX_10_7916)
        except PathAccessError:
            pass

    if a_slug_title == b_slug_title:
        try:
            a_subtitles = glom(a, "extra.subtitle") or []
            b_subtitles = glom(b, "extra.subtitle") or []
            for a_sub in a_subtitles:
                for b_sub in b_subtitles:
                    if slugify_string(a_sub) != slugify_string(b_sub):
                        return Verify(Status.DIFFERENT, Reason.SUBTITLE)
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
                                                         int(b_release_year)) > 4:
                return Verify(Status.DIFFERENT, Reason.YEAR)
            return Verify(Status.EXACT, Reason.TITLE_AUTHOR_MATCH)

    if (len(a.get("title", "").split()) == 1 and re.match(r".*[.][a-z]{2,3}", a.get("title", ""))
            or len(b.get("title", "").split()) == 1
            and re.match(r".*[.][a-z]{2,3}$", b.get("title", ""))):
        if a.get("title") != b.get("title"):
            return Verify(Status.DIFFERENT, Reason.TITLE_FILENAME)

    if a.get("title") and a.get("title") == b.get("title"):
        if a_release_year and b_release_year:
            if abs(int(a_release_year) - int(b_release_year)) > 2:
                return Verify(Status.DIFFERENT, Reason.YEAR)

    if contains_chemical_formula(a_slug_title) or contains_chemical_formula(b_slug_title) and (
            a_slug_title != b_slug_title):
        return Verify(Status.DIFFERENT, Reason.CHEM_FORMULA)

    if len(a_slug_title) < 10 and a_slug_title != b_slug_title:
        return Verify(Status.AMBIGUOUS, Reason.SHORT_TITLE)

    if re.search(r'\d+', a_slug_title) and a_slug_title != b_slug_title and num_project(
            a_slug_title) == num_project(b_slug_title):
        return Verify(Status.DIFFERENT, Reason.NUM_DIFF)

    if a_slug_title and b_slug_title and a_slug_title == b_slug_title:
        if a_authors and len(a_authors & b_authors) > 0:
            if arxiv_id_a is not None and arxiv_id_b is None or arxiv_id_a is None and arxiv_id_b is not None:
                return Verify(Status.STRONG, Reason.PREPRINT_PUBLISHED)

    if a_slug_title and b_slug_title and a_slug_title.strip().replace(
            " ", "") == b_slug_title.strip().replace(" ", ""):
        if len(a_slug_authors & b_slug_authors) > 0:
            # At this point, year might differ, e.g.
            # https://fatcat.wiki/release/2n7pyugxenb73gope52bn6m2ru vs
            # https://fatcat.wiki/release/p4bettvcszgn5d3zls5ogdjk4u (found via refs).
            if a_release_year and b_release_year and abs(int(a_release_year) -
                                                         int(b_release_year)) > 4:
                return Verify(Status.DIFFERENT, Reason.YEAR)
            return Verify(Status.STRONG, Reason.SLUG_TITLE_AUTHOR_MATCH)

    # if any([a_authors, b_authors]) and not (a_authors and b_authors):
    # Does not cover case, where both authors are empty.
    if a_release_year == b_release_year and a_title_lower == b_title_lower:
        if ((dict_key_exists(a, "ext_ids.pmid") and dict_key_exists(b, "ext_ids.doi"))
                or (dict_key_exists(b, "ext_ids.pmid") and dict_key_exists(a, "ext_ids.doi"))):
            return Verify(Status.STRONG, Reason.PMID_DOI_PAIR)

    # Two JSTOR items will probably be different.
    try:
        a_jstor_id = glom(a, "ext_ids.jstor")
        b_jstor_id = glom(b, "ext_ids.jstor")
        if a_jstor_id != b_jstor_id:
            return Verify(Status.DIFFERENT, Reason.JSTOR_ID)
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
                a_doi, "10.1126") and doi_prefix(a_doi) == doi_prefix(b_doi):
            return Verify(Status.DIFFERENT, Reason.SHARED_DOI_PREFIX)
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
        num_authors = min(len(a_trimmed), len(b_trimmed))
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
            if (num_authors < 3 and avg_score > 0.9) or (num_authors >= 3 and avg_score > 0.5):
                return Verify(Status.STRONG, Reason.TOKENIZED_AUTHORS)
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
            return Verify(Status.STRONG, Reason.JACCARD_AUTHORS)

        # TODO: This misses spelling differences, e.g.
        # https://fatcat.wiki/release/7nbcgsohrrak5cuyk6dnit6ega and
        # https://fatcat.wiki/release/q66xv7drk5fnph7enwwlkyuwqm
        return Verify(Status.DIFFERENT, Reason.CONTRIB_INTERSECTION_EMPTY)

    # mark choicereview articles as ambiguous, as they seem to be behind a paywall
    try:
        a_doi = glom(a, "ext_ids.doi")
        b_doi = glom(b, "ext_ids.doi")
        if has_doi_prefix(a_doi, "10.5860") or has_doi_prefix(b_doi, "10.5860"):
            return Verify(Status.AMBIGUOUS, Reason.CUSTOM_PREFIX_10_5860_CHOICE_REVIEW)
    except PathAccessError:
        pass

    # If pages exists, but differ too much, bail out.
    # https://fatcat.wiki/release/tm3gaiumkvb3xc7t3i6suna6u4
    # https://fatcat.wiki/release/r6dj63wh3zcrrolisn6xuacnve
    try:
        a_parsed_pages = parse_page_string(glom(a, "pages"))
        b_parsed_pages = parse_page_string(glom(b, "pages"))
        if abs(a_parsed_pages.count - b_parsed_pages.count) > 5:
            return Verify(Status.DIFFERENT, Reason.PAGE_COUNT)
    except (ValueError, PathAccessError):
        pass

    # A variant of translated titles, e.g.
    # https://fatcat.wiki/release/search?q=%22A+nova+classifica%C3%A7%C3%A3o+dos+tumores+da+mama+%22
    try:
        a_container_id = glom(a, "container_id")
        b_container_id = glom(b, "container_id")
        if a_authors == b_authors and a_container_id == b_container_id and a_release_year == b_release_year and a_title != b_title and (
                a_title in b_title or b_title in a_title):
            return Verify(Status.STRONG, Reason.TITLE_ARTIFACT)
    except PathAccessError:
        pass

    return Verify(Status.AMBIGUOUS, Reason.UNKNOWN)
