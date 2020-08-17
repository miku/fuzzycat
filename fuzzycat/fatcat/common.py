# coding: utf-8
"""
Adapter for fatcat and fatcat entities.
"""

import collections
from enum import Enum
from typing import Dict, List, Type, Union

from fatcat_openapi_client import (ApiException, ContainerEntity, DefaultApi, ReleaseEntity,
                                   ReleaseExtIds, WorkEntity)

from fuzzycat.fatcat.api_auth import public_api
from fuzzycat.fatcat.entities import entity_from_dict, entity_from_json


class MatchStatus(Enum):
    """
    When matching two entities, use these levels to express match strength.
    When in doubt, use AMBIGIOUS. DIFFERENT should be used only, when it is
    certain, that items do not match.
    """

    EXACT = 0
    STRONG = 1
    WEAK = 2
    AMBIGIOUS = 3
    DIFFERENT = 4


def compare_ext_ids(a: ReleaseExtIds, b: ReleaseExtIds) -> Dict[str, int]:
    """
    Returns a dictionary with number of existing, matching and differing
    identifier between entity a and b. TODO(martin): It might be helpful to
    have some mapping service, that would relate qid to doi, or a mag to a
    jstor id, if this information is known.
    """
    counter = collections.Counter({"a": 0, "b": 0, "both": 0, "hits": 0, "misses": 0})
    attrs = (
        "doi",
        "wikidata_qid",
        "isbn13",
        "pmid",
        "pmcid",
        "core",
        "arxiv",
        "jstor",
        "ark",
        "mag",
    )
    for attr in attrs:
        v = getattr(a, attr)
        w = getattr(b, attr)
        if v:
            counter["a"] += 1
        if w:
            counter["b"] += 1
        if not v or not w:
            continue
        counter["both"] += 1
        if v == w:
            counter["hits"] += 1
        else:
            counter["misses"] += 1
    return counter


def fetch_container_list(
    ids: List[str],
    api: DefaultApi = None,
) -> List[ContainerEntity]:
    """
    Fetch a list of containers from the API.
    """
    if api is None:
        api = public_api("https://api.fatcat.wiki/v0")
    result = []
    for id in ids:
        try:
            ce = api.get_container(id)
            result.append(ce)
        except ApiException as exc:
            if exc.status == 404:
                print("[err] failed to fetch container: {}".format(id), file=sys.stderr)
                continue
            raise
    return result


def fetch_release_list(
    ids: List[str],
    api: DefaultApi = None,
) -> List[ReleaseEntity]:
    """
    Returns a list of entities. Some entities might be missing. Return all that
    are accessible.
    """
    if api is None:
        api = public_api("https://api.fatcat.wiki/v0")
    result = []
    for id in ids:
        try:
            re = api.get_release(id, hide="refs,abstracts", expand="container")
            result.append(re)
        except ApiException as exc:
            if exc.status == 404:
                print("[err] failed to fetch release: {}".format(id), file=sys.stderr)
                continue
            raise
    return result


def entity_comparable_attrs(
    a: Union[ContainerEntity, ReleaseEntity],
    b: Union[ContainerEntity, ReleaseEntity],
    entity_type: Union[Type[ContainerEntity], Type[ReleaseEntity]],
) -> List[str]:
    """
    Return a list of top-level attributes, which are defined on both entities
    (i.e. we could actually compare them).
    """
    attrs = entity_type.attribute_map.keys()
    comparable_attrs = []
    for attr in attrs:
        if getattr(a, attr) is None:
            continue
        if getattr(b, attr) is None:
            continue
        comparable_attrs.append(attr)
    return comparable_attrs


def response_to_entity_list(response, size=5, entity_type=ReleaseEntity, api=None):
    """
    Convert an elasticsearch result to a list of entities. Accepts both a
    dictionary and an elasticsearch_dsl.response.Response.

    We take the ids from elasticsearch and retrieve entities via API.
    """
    if isinstance(response, dict):
        ids = [hit["_source"]["ident"] for hit in response["hits"]["hits"]][:size]
    elif isinstance(response, elasticsearch_dsl.response.Response):
        ids = [hit.to_dict().get("ident") for hit in response]

    if entity_type == ReleaseEntity:
        return fetch_release_list(ids, api=api)
    if entity_type == ContainerEntity:
        return fetch_container_list(ids, api=api)

    raise ValueError("invalid entity type: {}".format(entity_type))


def exact_release_match(a: ReleaseEntity, b: ReleaseEntity) -> bool:
    """
    Currently, entities implement comparison through object dictionaries.
    """
    return a == b


def exact_work_match(a: WorkEntity, b: WorkEntity) -> bool:
    """
    Currently, entities implement comparison through object dictionaries.
    """
    return a == b
