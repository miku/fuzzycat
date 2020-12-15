import elasticsearch
from fatcat_openapi_client import ContainerEntity, ReleaseEntity

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
        s = (
            elasticsearch_dsl.Search(using=es, index="fatcat_release")
            .query("term", **{es_field: value})
            .extra(size=size)
        )
        print(s)
        resp = s.execute()
        if len(resp) > 0:
            return response_to_entity_list(resp, entity_type=ReleaseEntity)

    body = {
        "query": {"match": {"title": {"query": release.title, "operator": "AND"}}},
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
