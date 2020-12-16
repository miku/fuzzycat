from fuzzycat.matching import anything_to_entity, match_release_fuzzy
from fatcat_openapi_client import ReleaseEntity
import pytest
import elasticsearch
import logging

logger = logging.getLogger('test_matching')
logger.setLevel(logging.DEBUG)


@pytest.fixture
def es_client():
    return elasticsearch.Elasticsearch(["https://search.fatcat.wiki:443"])


@pytest.mark.skip
def test_match_release_fuzzy(es_client):
    cases = (("wtv64ahbdzgwnan7rllwr3nurm", 2), )
    for case, count in cases:
        entity = anything_to_entity(case, ReleaseEntity)
        logger.info(entity.title)

        result = match_release_fuzzy(entity, es=es_client)
        logger.info("given: {}".format(entity.title))
        logger.info("found: {}".format(len(result)))
        assert len(result) == count
