from enum import Enum


class Status(str, Enum):
    """
    Match status.
    """
    AMBIGUOUS = 'ambigiuous'
    DIFFERENT = 'different'
    EXACT = 'exact'
    STRONG = 'strong'
    WEAK = 'weak'


class OK(str, Enum):
    """
    Reason for assuming we have a match.
    """
    ARXIV_VERSION = 'ok.arxiv_version'
    DATACITE_RELATED_ID = 'ok.datacite_related_id'
    DOI = 'ok.doi'
    DUMMY = 'ok.dummy'
    FIGSHARE_VERSION = 'ok.figshare_version'
    PREPRINT_PUBLISHED = 'ok.preprint_published'
    SLUG_TITLE_AUTHOR_MATCH = 'ok.slug_title_author_match'
    TITLE_AUTHOR_MATCH = 'ok.title_author_match'
    TOKENIZED_AUTHORS = 'ok.tokenized_authors'


class Miss(str, Enum):
    """
    Reasons indicating mismatch.
    """
    APPENDIX = 'miss.appendix'
    ARXIV_VERSION = 'miss.arxiv_version'
    BLACKLISTED = 'miss.blacklisted'
    BLACKLISTED_FRAGMENT = 'miss.blacklisted_fragment'
    BOOK_CHAPTER = 'miss.book_chapter'
    CHEM_FORMULA = 'miss.chem_formula'
    COMPONENT = 'miss.component'
    CONTRIB_INTERSECTION_EMPTY = 'miss.contrib_intersection_empty'
    CUSTOM_VHS = 'miss.vhs'  # https://fatcat.wiki/release/44gk5ben5vghljq6twm7lwmxla
    DATASET_DOI = 'miss.dataset_doi'
    NUM_DIFF = 'miss.num_diff'
    RELEASE_TYPE = 'miss.release_type'
    SHORT_TITLE = 'miss.short_title'
    SUBTITLE = 'miss.subtitle'
    TITLE_FILENAME = 'miss.title_filename'
    YEAR = 'miss.year'
