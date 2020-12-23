import os
import re
import sys
from typing import List, Optional, Type, Union

import elasticsearch
import elasticsearch_dsl
import fatcat_openapi_client
import requests
from dynaconf import Dynaconf
from fatcat_openapi_client import ContainerEntity, DefaultApi, ReleaseEntity
from fatcat_openapi_client.rest import ApiException

from fuzzycat.entities import entity_from_dict, entity_from_json

settings = Dynaconf(envvar_prefix="FUZZYCAT")
FATCAT_API_URL = settings.get("FATCAT_API_URL", "https://api.fatcat.wiki/v0")


def match_release_fuzzy(
    release: ReleaseEntity,
    size: int = 5,
    es: Optional[Union[str, Type[elasticsearch.client.Elasticsearch]]] = None,
    api: DefaultApi = None,
) -> List[ReleaseEntity]:
    """
    Given a release entity, return a number similar release entities from
    fatcat using Elasticsearch.

    TODO: rename "es" parameter to "es_client", which would be clearer
    """
    assert isinstance(release, ReleaseEntity)

    if size is None or size == 0:
        size = 10000  # or any large number

    if isinstance(es, str):
        es = elasticsearch.Elasticsearch([es])
    if es is None:
        es = elasticsearch.Elasticsearch()
    if api is None:
        api = public_api(FATCAT_API_URL)

    # Try to match by external identifier.
    # TODO: use api, ability to disable; benchmark
    ext_ids = release.ext_ids
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
        "doaj",
        "dblp",
        "oai",
    )
    for attr in attrs:
        value = getattr(ext_ids, attr)
        if not value:
            continue
        r = api.lookup_release(**{attr: value})
        if r:
            return r

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
        return response_to_entity_list(resp, entity_type=ReleaseEntity, api=api)

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
        return response_to_entity_list(resp, entity_type=ReleaseEntity, api=api)

    # TODO: perform more queries on other fields.
    return []


def public_api(host_uri):
    """
    Note: unlike the authenticated variant, this helper might get called even
    if the API isn't going to be used, so it's important that it doesn't try to
    actually connect to the API host or something.
    """
    conf = fatcat_openapi_client.Configuration()
    conf.host = host_uri
    return fatcat_openapi_client.DefaultApi(fatcat_openapi_client.ApiClient(conf))


def retrieve_entity_list(
    ids: List[str],
    api: DefaultApi = None,
    entity_type: Union[Type[ReleaseEntity], Type[ContainerEntity]] = ReleaseEntity,
) -> List[Union[Type[ReleaseEntity], Type[ContainerEntity]]]:
    """
    Retrieve a list of entities. Some entities might be missing. Return all
    that are accessible.
    """
    if api is None:
        api = public_api(FATCAT_API_URL)
    result = []
    if entity_type == ReleaseEntity:
        for id in ids:
            try:
                re = api.get_release(id, hide="refs,abstracts", expand="container")
                result.append(re)
            except ApiException as exc:
                if exc.status == 404:
                    print("[err] failed to retrieve release entity: {}".format(id), file=sys.stderr)
                else:
                    print("[err] api failed with {}: {}".format(exc.status, exc.message),
                          file=sys.stderr)
    elif entity_type == ContainerEntity:
        for id in ids:
            try:
                re = api.get_container(id)
                result.append(re)
            except ApiException as exc:
                if exc.status == 404:
                    print("[err] failed to retrieve container entity: {}".format(id),
                          file=sys.stderr)
                else:
                    print("[err] api failed with {}: {}".format(exc.status, exc.message),
                          file=sys.stderr)
    else:
        raise ValueError("[err] cannot retrieve ids {} of type {}".format(ids, entity_type))

    return result


def response_to_entity_list(response, size=5, entity_type=ReleaseEntity, api: DefaultApi = None):
    """
    Convert an elasticsearch result to a list of entities. Accepts both a
    dictionary and an elasticsearch_dsl.response.Response.

    We take the ids from elasticsearch and retrieve entities via API.
    """
    if isinstance(response, dict):
        ids = [hit["_source"]["ident"] for hit in response["hits"]["hits"]][:size]
        return retrieve_entity_list(ids, entity_type=entity_type, api=api)
    elif isinstance(response, elasticsearch_dsl.response.Response):
        ids = [hit.to_dict().get("ident") for hit in response]
        return retrieve_entity_list(ids, entity_type=entity_type, api=api)
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
        raise ValueError("cannot convert {}, only: {}".format(entity_type, names.keys()))
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
        # TODO: make index name configurable
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
