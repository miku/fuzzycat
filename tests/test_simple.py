"""
These basically all hit external network services.
"""

import pytest
import elasticsearch

from fuzzycat.simple import *
from fuzzycat.config import settings


@pytest.fixture
def es_client():
    return elasticsearch.Elasticsearch(
        [settings.get("FATCAT_SEARCH_URL", "https://search.fatcat.wiki:443")])


def test_close_fuzzy_unstructured_matches(es_client):

    matches = close_fuzzy_unstructured_matches(
        """Cunningham HB, Weis JJ, Taveras LR, Huerta S. Mesh migration following abdominal hernia repair: a comprehensive review. Hernia. 2019 Apr;23(2):235-243. doi: 10.1007/s10029-019-01898-9. Epub 2019 Jan 30. PMID: 30701369.""",
        es_client=es_client)

    assert matches
    assert matches[0].status.name == "EXACT"
    assert matches[0].release.ext_ids.doi == "10.1007/s10029-019-01898-9"


def test_close_fuzzy_biblio_matches(es_client):

    matches = close_fuzzy_biblio_matches(dict(
        title="Mesh migration following abdominal hernia repair: a comprehensive review",
        first_author="Cunningham",
        year=2019,
        journal="Hernia",
    ),
                                         es_client=es_client)

    assert matches
    # TODO: should be "STRONG" or "WEAK" without all authors?
    assert matches[0].status.name in ("STRONG", "WEAK", "AMBIGUOUS")
    assert matches[0].release.ext_ids.doi == "10.1007/s10029-019-01898-9"
