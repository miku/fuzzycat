"""
This file contains simple high-level functions that call in to match, verify,
and unstructured parsing routines.

    close_fuzzy_release_matches(release) -> List[FuzzyReleaseMatchResult]
    close_fuzzy_biblio_matches(biblio) -> List[FuzzyReleaseMatchResult]
    close_fuzzy_unstructured_matches(unstructured) -> List[FuzzyReleaseMatchResult]

Each function takes additional arguments:

    es_client
    fatcat_api_client
    match_limit

Each also has a "closest" variant, which returns just the single highest-rated
match.
"""

from dataclasses import dataclass
from typing import Any, List, Optional

from fatcat_openapi_client import ReleaseContrib, ReleaseEntity, ReleaseExtIds

from fuzzycat.common import Reason, Status
from fuzzycat.entities import entity_to_dict
from fuzzycat.grobid_unstructured import grobid_parse_unstructured
from fuzzycat.matching import match_release_fuzzy
from fuzzycat.verify import verify


@dataclass
class FuzzyReleaseMatchResult:
    status: Status
    reason: Reason
    release: ReleaseEntity


# this map used to establish priority order of verified matches
STATUS_SORT = {
    Status.TODO: 0,
    Status.EXACT: 10,
    Status.STRONG: 20,
    Status.WEAK: 30,
    Status.AMBIGUOUS: 40,
    Status.DIFFERENT: 60,
}


def close_fuzzy_release_matches(release: ReleaseEntity,
                                es_client: Any,
                                fatcat_api_client: Optional[Any] = None,
                                match_limit: int = 5) -> Optional[FuzzyReleaseMatchResult]:
    """
    This high-level helper function runs a fuzzy match (using elasticsearch),
    verifies all the results, and returns the "closest" matching results (if
    any).

    es_client is required, and used in the matcing process.

    fatcat_api_client is optional and used both for entity-to-dict conversion
    efficiency and for fetching current entities from the fatcat API

    match_limit sets the maximum result size from the inital fuzzy match call

    Returns an empty list if there was no match of any kind, or a sorted list
    of simple result objects (FuzzyReleaseMatchResult dataclass) with fields:

        status: fuzzycat.common.Status
        reason: fuzzycat.common.Reason
        release: ReleaseEntity

    Status is one of the fuzzycat.common.Status, with "strongest match" in this
    sorted order:

    - EXACT
    - STRONG
    - WEAK
    - AMBIGUOUS

    DIFFERENT and TODO matches are never returned.

    Eg, if there is any EXACT match that is always returned; an AMBIGIOUS
    result is only returned if all the candidate matches were ambiguous.
    """

    candidates = match_release_fuzzy(release, size=match_limit, es=es_client)
    if not candidates:
        return None

    release_dict = entity_to_dict(release, api_client=fatcat_api_client)

    # list of tuple of (Verify, ReleaseEntity)
    verified = [(
        verify(release_dict, entity_to_dict(c, api_client=fatcat_api_client)),
        c,
    ) for c in candidates]

    # list of FuzzyReleaseMatchResult, with TODO and DIFFERENT removed
    verified = [
        FuzzyReleaseMatchResult(v[0].status, v[0].reason, v[1]) for v in verified
        if v[0].status not in [Status.TODO, Status.DIFFERENT]
    ]

    return sorted(verified, key=lambda v: STATUS_SORT[v.status])


def closest_fuzzy_release_match(release: ReleaseEntity,
                                es_client: Any,
                                fatcat_api_client: Optional[Any] = None,
                                match_limit: int = 5) -> Optional[FuzzyReleaseMatchResult]:
    """
    Single-result variant of close_fuzzy_release_matches()
    """
    matches = close_fuzzy_release_matches(
        release,
        es_client=es_client,
        fatcat_api_client=fatcat_api_client,
        match_limit=match_limit,
    )
    if matches:
        return matches[0]
    else:
        return None


def close_fuzzy_unstructured_matches(raw_citation: str,
                                     es_client: Any,
                                     fatcat_api_client: Optional[Any] = None,
                                     match_limit: int = 5) -> List[FuzzyReleaseMatchResult]:
    """
    Variation of close_fuzzy_release_matches() which first parses an
    unstructured citation string, then finds close matches.

    TODO: pass-through GROBID API configuration?
    """
    release = grobid_parse_unstructured(raw_citation)
    if not release:
        return None
    return close_fuzzy_release_matches(
        release,
        es_client=es_client,
        fatcat_api_client=fatcat_api_client,
        match_limit=match_limit,
    )


def closest_fuzzy_unstructured_match(raw_citation: str,
                                     es_client: Any,
                                     fatcat_api_client: Optional[Any] = None,
                                     match_limit: int = 5) -> List[FuzzyReleaseMatchResult]:
    """
    Single-result variant of close_fuzzy_release_matches()
    """
    matches = close_fuzzy_unstructured_matches(
        raw_citation,
        es_client=es_client,
        fatcat_api_client=fatcat_api_client,
        match_limit=match_limit,
    )
    if matches:
        return matches[0]
    else:
        return None


def biblio_to_release(biblio: dict) -> ReleaseEntity:
    """
    Helper for close_fuzzy_biblio_matches() et al
    """
    contribs = []
    if biblio.get('authors'):
        for a in biblio['authors']:
            contribs.append(
                ReleaseContrib(
                    raw_name=a.get('name'),
                    given_name=a.get('given_name'),
                    surname=a.get('surname'),
                ))
    elif biblio.get('author_names'):
        for a in biblio['author_names']:
            contribs.append(ReleaseContrib(raw_name=a))
    elif biblio.get('first_author'):
        contribs.append(ReleaseContrib(raw_name=biblio['first_author']))
    release = ReleaseEntity(
        title=biblio.get("title"),
        ext_ids=ReleaseExtIds(
            doi=biblio.get("doi"),
            pmid=biblio.get("pmid"),
            pmcid=biblio.get("pmcid"),
            arxiv=biblio.get("arxiv_id"),
        ),
        volume=biblio.get("volume"),
        issue=biblio.get("issue"),
        pages=biblio.get("pages") or biblio.get("first_page"),
        publisher=biblio.get("publisher"),
        release_stage=biblio.get("release_stage"),
        release_type=biblio.get("release_type"),
        extra=dict(),
    )
    if biblio.get('journal'):
        release.extra['container_name'] = biblio['journal']
    elif biblio.get('conference'):
        release.extra['container_name'] = biblio['conference']
    if biblio.get('year'):
        year = biblio['year']
        if isinstance(year, str) and len(year) >= 4 and year[0:4].isdigit():
            release.release_year = int(year[0:4])
        elif isinstance(year, int):
            release.release_year = year
    elif biblio.get('date'):
        date = biblio['date']
        if isinstance(date, str) and len(date) >= 4 and date[0:4].isdigit():
            release.release_year = int(date[0:4])
    return release


def close_fuzzy_biblio_matches(biblio: dict,
                               es_client: Any,
                               fatcat_api_client: Optional[Any] = None,
                               match_limit: int = 5) -> List[FuzzyReleaseMatchResult]:
    """
    Variation of close_fuzzy_release_matches() which takes bibliographic fields
    as arguments.

    Biblio fields which are handled include:

        title
        journal
        or: conference
        authors
            name
            given_name
            surname
        or: author_names (List[str])
        or: first_author (str)
        year
        date
        volume
        issue
        pages
        or: first_page
        publisher
        doi
        pmid
        arxiv_id
        release_type (eg, 'journal-article', 'book', 'dataset')
        release_stage
    """
    release = biblio_to_release(biblio)
    return close_fuzzy_release_matches(
        release,
        es_client=es_client,
        fatcat_api_client=fatcat_api_client,
        match_limit=match_limit,
    )


def closest_fuzzy_biblio_match(biblio: dict,
                               es_client: Any,
                               fatcat_api_client: Optional[Any] = None,
                               match_limit: int = 5) -> List[FuzzyReleaseMatchResult]:
    """
    Single-result variant of close_fuzzy_biblio_matches()
    """
    matches = close_fuzzy_biblio_matches(
        biblio,
        es_client=es_client,
        fatcat_api_client=fatcat_api_client,
        match_limit=match_limit,
    )
    if matches:
        return matches[0]
    else:
        return None
