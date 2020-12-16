import os
import re
from typing import List, Type, Union

import elasticsearch
import elasticsearch_dsl
import requests
from fatcat_openapi_client import ContainerEntity, ReleaseEntity

from fuzzycat.entities import entity_from_dict, entity_from_json


def match_release_fuzzy(release: ReleaseEntity, size=5, es=None) -> List[ReleaseEntity]:
    """
    Given a release entity, return a number similar release entities from
    fatcat using Elasticsearch.
    """
    assert isinstance(release, ReleaseEntity)

    if size is None or size == 0:
        size = 10000  # or any large number

    if isinstance(es, str):
        es = elasticsearch.Elasticsearch([es])
    if es is None:
        es = elasticsearch.Elasticsearch()

    # Try to match by external identifier.
    ext_ids = release.ext_ids
    attrs = {
        "doi": "doi",
        "wikidata_qid": "wikidata_qid",
        "isbn13": "isbn13",
        "pmid": "pmid",
        "pmcid": "pmcid",
        "core": "code_id",
        "arxiv": "arxiv_id",
        "jstor": "jstor_id",
        "ark": "ark_id",
        "mag": "mag_id",
    }
    for attr, es_field in attrs.items():
        value = getattr(ext_ids, attr)
        if not value:
            continue
        s = (elasticsearch_dsl.Search(using=es,
                                      index="fatcat_release").query("term", **{
                                          es_field: value
                                      }).extra(size=size))
        print(s)
        resp = s.execute()
        if len(resp) > 0:
            return response_to_entity_list(resp, entity_type=ReleaseEntity)

    body = {
        "query": {
            "match": {
                "title": {
                    "query": release.title,
                    "operator": "AND"
                }
            }
        },
        "size": size,
    }
    resp = es.search(body=body, index="fatcat_release")
    if resp["hits"]["total"] > 0:
        return response_to_entity_list(resp, entity_type=ReleaseEntity)

    # Get fuzzy.
    # https://www.elastic.co/guide/en/elasticsearch/reference/current/common-options.html#fuzziness
    body = {
        "query": {
            "match": {
                "title": {
                    "query": release.title,
                    "operator": "AND",
                    "fuzziness": "AUTO",
                }
            }
        },
        "size": size,
    }
    resp = es.search(body=body, index="fatcat_release")
    if resp["hits"]["total"] > 0:
        return response_to_entity_list(resp, entity_type=ReleaseEntity)

    # TODO: perform more queries on other fields.
    return []


def response_to_entity_list(response, size=5, entity_type=ReleaseEntity):
    """
    Convert an elasticsearch result to a list of entities. Accepts both a
    dictionary and an elasticsearch_dsl.response.Response.

    We take the ids from elasticsearch and retrieve entities via API.
    """
    if isinstance(response, dict):
        ids = [hit["_source"]["ident"] for hit in response["hits"]["hits"]][:size]
        return retrieve_entity_list(ids, entity_type=entity_type)
    elif isinstance(response, elasticsearch_dsl.response.Response):
        ids = [hit.to_dict().get("ident") for hit in response]
        return retrieve_entity_list(ids, entity_type=entity_type)
    else:
        raise ValueError("cannot convert {}".format(response))


def anything_to_entity(
    s: str,
    entity_type: Union[Type[ContainerEntity], Type[ReleaseEntity]],
    api_url: str = "https://api.fatcat.wiki/v0",
    es_url: str = "https://search.fatcat.wiki",
) -> Union[ContainerEntity, ReleaseEntity]:
    """
    Convert a string to a given entity type. This function may go out to the
    fatcat API or elasticsearch and hence is expensive.
    """
    names = {
        ContainerEntity: "container",
        ReleaseEntity: "release",
    }
    if not entity_type in names:
        raise ValueError("cannot convert {} - only: {}".format(entity_type, names.keys()))
    entity_name = names[entity_type]

    if s is None:
        raise ValueError("no entity found")

    if os.path.exists(s):
        with open(s) as f:
            return entity_from_json(f.read(), entity_type)

    match = re.search("/?([a-z0-9]{26})$", s)
    if match:
        url = "{}/{}/{}".format(api_url, entity_name, match.group(1))
        resp = requests.get(url)
        if resp.status_code == 200:
            return entity_from_json(resp.text, entity_type)
        if resp.status_code == 404:
            raise ValueError("entity not found: {}".format(url))

    if re.match("[0-9]{4}(-)?[0-9]{3,3}[0-9xx]", s):
        url = "{}/fatcat_{}/_search?q=issns:{}".format(es_url, entity_name, s)
        doc = requests.get(url).json()
        if doc["hits"]["total"] == 1:
            ident = doc["hits"]["hits"][0]["_source"]["ident"]
            url = "{}/{}/{}".format(api_url, entity_name, ident)
            return entity_from_json(requests.get(url).text, entity_type)

    if entity_name == "container":
        return entity_from_dict({"name": s}, entity_type)
    elif entity_name == "release":
        return entity_from_dict({"title": s, "ext_ids": {}}, entity_type)
    else:
        raise ValueError("unhandled entity type: {}".format(entity_type))
