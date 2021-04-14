import pytest

from fuzzycat.grobid_unstructured import grobid_api_process_citation, grobid_parse_unstructured, grobid_ref_to_release, transform_grobid_ref_xml


def test_grobid_ref_to_release():

    d = {
        'title':
        "some title",
        'doi':
        '10.1234/5678',
        'journal':
        'some journal',
        'authors': [
            {
                'name': 'ahab sailor',
                'given_name': 'ahab',
                'surname': 'sailor'
            },
            {
                'name': 'mary jane',
                'given_name': 'mary',
                'surname': 'jane'
            },
        ],
    }
    r = grobid_ref_to_release(d)
    assert r.title == d['title']
    assert r.ext_ids.doi == d['doi']
    assert r.extra['container_name'] == d['journal']
    assert r.contribs[0].surname == d['authors'][0]['surname']
    assert r.contribs[1].raw_name == d['authors'][1]['name']


def test_transform_grobid_ref_xml():
    citation_xml = """
<biblStruct >
    <analytic>
        <title level="a" type="main">Mesh migration following abdominal hernia repair: a comprehensive review</title>
        <author>
            <persName
                xmlns="http://www.tei-c.org/ns/1.0">
                <forename type="first">H</forename>
                <forename type="middle">B</forename>
                <surname>Cunningham</surname>
            </persName>
        </author>
        <author>
            <persName
                xmlns="http://www.tei-c.org/ns/1.0">
                <forename type="first">J</forename>
                <forename type="middle">J</forename>
                <surname>Weis</surname>
            </persName>
        </author>
        <author>
            <persName
                xmlns="http://www.tei-c.org/ns/1.0">
                <forename type="first">L</forename>
                <forename type="middle">R</forename>
                <surname>Taveras</surname>
            </persName>
        </author>
        <author>
            <persName
                xmlns="http://www.tei-c.org/ns/1.0">
                <forename type="first">S</forename>
                <surname>Huerta</surname>
            </persName>
        </author>
        <idno type="DOI">10.1007/s10029-019-01898-9</idno>
        <idno type="PMID">30701369</idno>
    </analytic>
    <monogr>
        <title level="j">Hernia</title>
        <imprint>
            <biblScope unit="volume">23</biblScope>
            <biblScope unit="issue">2</biblScope>
            <biblScope unit="page" from="235" to="243" />
            <date type="published" when="2019-01-30" />
        </imprint>
    </monogr>
</biblStruct>"""

    d = transform_grobid_ref_xml(citation_xml)
    assert d['title'] == "Mesh migration following abdominal hernia repair: a comprehensive review"
    assert d['authors'][2]['given_name'] == "L"
    assert d['authors'][2]['surname'] == "Taveras"
    assert d['authors'][2]['name'] == "L R Taveras"
    assert d['doi'] == "10.1007/s10029-019-01898-9"
    assert d['pmid'] == "30701369"
    assert d['date'] == "2019-01-30"
    assert d['pages'] == "235-243"
    assert d['volume'] == "23"
    assert d['issue'] == "2"
    assert d['journal'] == "Hernia"


def test_grobid_parse_unstructured():
    """
    NOTE: this test makes live network requests to GROBID
    """

    r = grobid_parse_unstructured("blah")
    assert r is None

    r = grobid_parse_unstructured(
        """Cunningham HB, Weis JJ, Taveras LR, Huerta S. Mesh migration following abdominal hernia repair: a comprehensive review. Hernia. 2019 Apr;23(2):235-243. doi: 10.1007/s10029-019-01898-9. Epub 2019 Jan 30. PMID: 30701369."""
    )
    assert r.title == "Mesh migration following abdominal hernia repair: a comprehensive review"
    assert r.contribs[0].surname == "Cunningham"
    assert r.contribs[1].surname == "Weis"
    assert r.contribs[2].surname == "Taveras"
    assert r.contribs[3].surname == "Huerta"
    assert r.extra['container_name'] == "Hernia"
    assert r.release_year == 2019
    assert r.volume == "23"
    assert r.issue == "2"
    assert r.pages == "235-243"
    assert r.ext_ids.doi == "10.1007/s10029-019-01898-9"
    assert r.ext_ids.pmid == "30701369"


def test_grobid_parse_unstructured_timeout():
    """
    NOTE: this test makes live network requests to GROBID
    """
    with pytest.raises(TimeoutError):
        grobid_parse_unstructured("blah", timeout=0.000001)
