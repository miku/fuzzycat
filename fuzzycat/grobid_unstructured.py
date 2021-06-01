"""
Helper functions to parse an unstructured citation string using GROBID, then
fuzzy match using the result.

- try to parse string with GROBID REST API call
- transform the GROBID XML response to a simple dict/struct

TODO: more general versions which handle multiple reference strings in a batch?
"""

import io
import sys
import xml.etree.ElementTree as ET
from typing import Optional

import requests
from fatcat_openapi_client import ReleaseContrib, ReleaseEntity, ReleaseExtIds

from fuzzycat.config import settings
from fuzzycat.grobid2json import biblio_info

GROBID_API_BASE = settings.get("GROBID_API_BASE", "https://grobid.qa.fatcat.wiki")


def grobid_api_process_citation(raw_citation: str,
                                grobid_api_base: str = GROBID_API_BASE,
                                timeout: float = 20.0) -> Optional[str]:
    """
    Process a single citation string using GROBID API, returning a TEI-XML response.

    Raises python TimeoutError if there was a network or request timeout.

    Raises a 'requests' error other unexpected failures (including network
    connection failures)
    """
    try:
        grobid_response = requests.post(
            grobid_api_base + "/api/processCitation",
            data={
                "citations": raw_citation,
                "consolidateCitations": 0,
            },
            timeout=timeout,
        )
    except requests.Timeout:
        raise TimeoutError("GROBID request (HTTP POST) timeout")

    if grobid_response.status_code == 204:
        return None
    elif grobid_response.status_code != 200:
        print(f"GROBID request (HTTP POST) failed: {grobid_response}", file=sys.stderr)
    grobid_response.raise_for_status()

    return grobid_response.text or None


def transform_grobid_ref_xml(raw_xml: str) -> Optional[dict]:
    """
    Parses GROBID XML for the case of a single reference/citation string (eg,
    not a full/propper TEI-XML fulltext document), and returns a dict.
    """
    # first, remove any xmlns stuff, for consistent parsign
    raw_xml = raw_xml.replace('xmlns="http://www.tei-c.org/ns/1.0"', "")
    tree = ET.parse(io.StringIO(raw_xml))
    root = tree.getroot()
    ref = biblio_info(root, ns="")
    if not any(ref.values()):
        return None
    return ref


def grobid_ref_to_release(ref: dict) -> ReleaseEntity:
    """
    Takes the dict returned by transform_grobid_ref_xml() and returns a partial
    ReleaseEntity object (for use with fuzzycat)
    """
    contribs = []
    for author in ref.get("authors") or []:
        contribs.append(
            ReleaseContrib(
                raw_name=author.get("name"),
                given_name=author.get("given_name"),
                surname=author.get("surname"),
            ))
    release = ReleaseEntity(
        title=ref.get("title"),
        contribs=contribs,
        volume=ref.get("volume"),
        issue=ref.get("issue"),
        pages=ref.get("pages"),
        ext_ids=ReleaseExtIds(
            doi=ref.get("doi"),
            pmid=ref.get("pmid"),
            pmcid=ref.get("pmcid"),
            arxiv=ref.get("arxiv_id"),
        ),
    )
    if ref.get("journal"):
        release.extra = {"container_name": ref.get("journal")}
    if ref.get("date"):
        if len(ref["date"]) >= 4 and ref["date"][0:4].isdigit():
            release.release_year = int(ref["date"][0:4])
        # TODO: try to parse 'date' into an ISO date format, and assign to release_date?
    return release


def grobid_parse_unstructured(raw_citation: str,
                              grobid_api_base: str = GROBID_API_BASE,
                              timeout: float = 20.0) -> Optional[ReleaseEntity]:
    """
    High-level wrapper to parse a raw citation string into a (partial) release
    entity.
    
    Returns None if it fails to parse.

    Raises various exceptions on network or remote errors.
    """
    ref_xml = grobid_api_process_citation(raw_citation,
                                          grobid_api_base=grobid_api_base,
                                          timeout=timeout)
    if not ref_xml:
        return None
    biblio_dict = transform_grobid_ref_xml(ref_xml)
    if not biblio_dict:
        return None
    return grobid_ref_to_release(biblio_dict)
