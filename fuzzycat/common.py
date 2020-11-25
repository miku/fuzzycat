from enum import Enum


class Status(str, Enum):
    """
    Match status.
    """
    EXACT = 'exact'
    DIFFERENT = 'different'
    STRONG = 'strong'
    WEAK = 'weak'
    AMBIGUOUS = 'ambigiuous'


class OK(str, Enum):
    """
    Reason for assuming we have a match.
    """
    ARXIV_VERSION = 'ok.arxiv_version'
    FIGSHARE_VERSION = 'ok.figshare_version'
    DUMMY = 'ok.dummy'
    TITLE_AUTHOR_MATCH = 'ok.title_author_match'
    PREPRINT_PUBLISHED = 'ok.preprint_published'
    SLUG_TITLE_AUTHOR_MATCH = 'ok.slug_title_author_match'
    TOKENIZED_AUTHORS = 'ok.tokenized_authors'
    DATACITE_RELATED_ID = 'ok.datacite_related_id'


class Miss(str, Enum):
    """
    Reasons indicating mismatch.
    """
    ARXIV_VERSION = 'miss.arxiv_version'
    BLACKLISTED = 'miss.blacklisted'
    BLACKLISTED_FRAGMENT = 'miss.blacklisted_fragment'
    CONTRIB_INTERSECTION_EMPTY = 'miss.contrib_intersection_empty'
    SHORT_TITLE = 'miss.short_title'
    YEAR = 'miss.year'
    CUSTOM_VHS = 'miss.vhs'  # https://fatcat.wiki/release/44gk5ben5vghljq6twm7lwmxla
    NUM_DIFF = 'miss.num_diff'
    DATASET_DOI = 'miss.dataset_doi'
    RELEASE_TYPE = 'miss.release_type'
    CHEM_FORMULA = 'miss.chem_formula'
    SUBTITLE = 'miss.subtitle'
    BOOK_CHAPTER = 'miss.book_chapter'
    TITLE_FILENAME = 'miss.title_filename'
    COMPONENT = 'miss.component'
    APPENDIX = 'miss.appendix'
