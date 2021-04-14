from fuzzycat.matching import anything_to_entity, match_release_fuzzy
from fuzzycat.entities import entity_from_dict
from fatcat_openapi_client import ReleaseEntity
import pytest
import elasticsearch
import logging
from dynaconf import Dynaconf

logger = logging.getLogger('test_matching')
logger.setLevel(logging.DEBUG)

settings = Dynaconf(envvar_prefix="FUZZYCAT")
FATCAT_SEARCH_URL = settings.get("FATCAT_SEARCH_URL", "https://search.fatcat.wiki:443")


@pytest.fixture
def es_client():
    return elasticsearch.Elasticsearch([FATCAT_SEARCH_URL])


def test_match_release_fuzzy(es_client, caplog):
    cases = (
        ("wtv64ahbdzgwnan7rllwr3nurm", 1),
        ("eqcgtpav3na5jh56o5vjsvb4ei", 1),
    )
    for i, (ident, count) in enumerate(cases):
        entity = anything_to_entity(ident, ReleaseEntity)

        result = match_release_fuzzy(entity, es=es_client)
        logger.info("[{}] given {}, found {}".format(i, entity.title, len(result)))
        assert len(result) == count

    # Partial data.
    cases = (
        ({
            "title": "digital libraries",
            "ext_ids": {}
        }, 5),
        ({
            "title": "The Future of Digital Scholarship",
            "contribs": [{
                "raw_name": "Costantino Thanos"
            }],
            "ext_ids": {}
        }, 5),
    )
    for i, (doc, count) in enumerate(cases):
        entity = entity_from_dict(doc, ReleaseEntity)
        result = match_release_fuzzy(entity, es=es_client)
        with caplog.at_level(logging.INFO):
            logging.info("[{}] given {}, found {}, {}".format(i, entity.title, len(result),
                                                              [v.title for v in result]))
        assert len(result) == count
