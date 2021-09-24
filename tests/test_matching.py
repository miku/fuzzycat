import logging
import warnings

import elasticsearch
import pytest
import requests
from fatcat_openapi_client import ReleaseEntity

from fuzzycat.entities import entity_from_dict
from fuzzycat.matching import anything_to_entity, match_release_fuzzy

warnings.filterwarnings(
    "ignore")  # InsecureRequestWarning: Unverified HTTPS request is being made to host ...

from fuzzycat.matching import anything_to_entity, match_release_fuzzy
from fuzzycat.config import settings
from fatcat_openapi_client import ReleaseEntity
import pytest
import elasticsearch
import logging

logger = logging.getLogger('test_matching')
logger.setLevel(logging.DEBUG)

# ad-hoc override search server with: FUZZYCAT_FATCAT_SEARCH_URL=localhost:9200 pytest ...
FATCAT_SEARCH_URL = settings.get("FATCAT_SEARCH_URL", "https://search.fatcat.wiki:443")


def is_not_reachable(url, timeout=3):
    return not is_reachable(url)


def is_reachable(url, timeout=3):
    """
    Return true, if URL is reachable and returns HTTP 200.
    """
    try:
        return requests.get(url, verify=False, timeout=timeout).ok
    except Exception:
        return False


@pytest.fixture
def es_client():
    return elasticsearch.Elasticsearch([FATCAT_SEARCH_URL])


@pytest.mark.skipif(
    is_not_reachable(FATCAT_SEARCH_URL),
    reason="{} not reachable, use e.g. FUZZYCAT_FATCAT_SEARCH_URL=localhost:9200 to override".
    format(FATCAT_SEARCH_URL))
def test_match_release_fuzzy(es_client, caplog):
    """
    This test is tied to the current index contents, so if that changes, this
    test may fail as well.
    """
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
            "title": "unlikelytitle",
            "ext_ids": {}
        }, 0),
        ({
            "title": "Imminent dystopia",
            "ext_ids": {}
        }, 2),
        ({
            "title": "",
            "contribs": [{
                "raw_name": "Aristoteles"
            }],
            "ext_ids": {}
        }, 5),
        # ({
        #     "title": "Letter",
        #     "contribs": [{"raw_name": "Claudel"}],
        #     "ext_ids": {}
        # }, 1),
        # ({
        #     "title": "The Future of Digital Scholarship",
        #     "contribs": [{
        #         "raw_name": "Costantino Thanos"
        #     }],
        #     "ext_ids": {}
        # }, 5),
    )
    for i, (doc, count) in enumerate(cases):
        entity = entity_from_dict(doc, ReleaseEntity)
        result = match_release_fuzzy(entity, es=es_client)
        with caplog.at_level(logging.INFO):
            logging.info("[{}] given title '{}', found {}, {}".format(i, entity.title, len(result),
                                                                      [v.title for v in result]))
        assert len(result) == count, doc
