from enum import Enum


class Status(str, Enum):
    """
    Match status.
    """
    AMBIGUOUS = 'ambiguous'
    DIFFERENT = 'different'
    EXACT = 'exact'
    STRONG = 'strong'
    WEAK = 'weak'
    TODO = 'todo'


class OK(str, Enum):
    """
    Reason for assuming we have a match.
    """
    ARXIV_VERSION = 'ok.arxiv_version'
    CUSTOM_BSI_SUBDOC = 'ok.custom_bsi_subdoc'
    CUSTOM_BSI_UNDATED = 'ok.custom_bsi_undated'
    CUSTOM_IEEE_ARXIV = 'ok.custom_ieee_arxiv'
    DATACITE_RELATED_ID = 'ok.datacite_related_id'
    DATACITE_VERSION = 'ok.datacite_version'
    DOI = 'ok.doi'
    DUMMY = 'ok.dummy'
    FIGSHARE_VERSION = 'ok.figshare_version'
    JACCARD_AUTHORS = 'ok.jaccard_authors'
    PMID_DOI_PAIR = 'ok.pmid_doi_pair'
    PREPRINT_PUBLISHED = 'ok.preprint_published'
    SLUG_TITLE_AUTHOR_MATCH = 'ok.slug_title_author_match'
    TITLE_AUTHOR_MATCH = 'ok.title_author_match'
    TOKENIZED_AUTHORS = 'ok.tokenized_authors'
    VERSIONED_DOI = 'ok.versioned_doi'
    WORK_ID = 'ok.work_id'


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
    CONTAINER = 'miss.container'
    CONTRIB_INTERSECTION_EMPTY = 'miss.contrib_intersection_empty'
    CUSTOM_IOP_MA_PATTERN = 'miss.custom_iop_ma_pattern'
    CUSTOM_PREFIX_10_14288 = 'miss.custom_prefix_10_14288'
    CUSTOM_PREFIX_10_5860_CHOICE_REVIEW = 'miss.custom_prefix_10_5860_choice_review'
    CUSTOM_PREFIX_10_7916 = 'miss.custom_prefix_10_7916'
    CUSTOM_VHS = 'miss.vhs'  # https://fatcat.wiki/release/44gk5ben5vghljq6twm7lwmxla
    DATASET_DOI = 'miss.dataset_doi'
    JSTOR_ID = 'miss.jstor_id'
    NUM_DIFF = 'miss.num_diff'
    PAGE_COUNT = 'miss.page_count'
    RELEASE_TYPE = 'miss.release_type'
    SHARED_DOI_PREFIX = 'miss.shared_doi_prefix'
    SHORT_TITLE = 'miss.short_title'
    SUBTITLE = 'miss.subtitle'
    TITLE_FILENAME = 'miss.title_filename'
    YEAR = 'miss.year'
