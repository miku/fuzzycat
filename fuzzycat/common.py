from enum import Enum


class Status(str, Enum):
    """
    Match status. The match status "TODO" is a placeholder, e.g. to trigger a
    test failure.

    TODO: FuzzyStatus, FuzzycatStatus, MatchVerifyStatus, MatchConfidence
    """
    AMBIGUOUS = 'ambiguous'
    DIFFERENT = 'different'
    EXACT = 'exact'
    STRONG = 'strong'
    WEAK = 'weak'
    TODO = 'todo'  # maybe UNIMPLEMENTED, TODO: change this after !MR92


class Reason(str, Enum):
    """
    Reason for assuming we have a match or miss. No hard rules on naming, maybe
    if a rule leans toward specific sources, you can use `CUSTOM_` as prefix.
    """
    APPENDIX = 'appendix'
    ARXIV_VERSION = 'arxiv_version'
    BLACKLISTED = 'blacklisted'
    BLACKLISTED_FRAGMENT = 'blacklisted_fragment'
    BOOK_CHAPTER = 'book_chapter'
    CHEM_FORMULA = 'chem_formula'
    COMPONENT = 'component'
    CONTAINER = 'container'
    CONTAINER_NAME_BLACKLIST = 'container_name_blacklist'
    CONTRIB_INTERSECTION_EMPTY = 'contrib_intersection_empty'
    CUSTOM_BSI_SUBDOC = 'custom_bsi_subdoc'
    CUSTOM_BSI_UNDATED = 'custom_bsi_undated'
    CUSTOM_IEEE_ARXIV = 'custom_ieee_arxiv'
    CUSTOM_IOP_MA_PATTERN = 'custom_iop_ma_pattern'
    CUSTOM_PREFIX_10_14288 = 'custom_prefix_10_14288'
    CUSTOM_PREFIX_10_5860_CHOICE_REVIEW = 'custom_prefix_10_5860_choice_review'
    CUSTOM_PREFIX_10_7916 = 'custom_prefix_10_7916'
    CUSTOM_VHS = 'vhs'  # https://fatcat.wiki/release/44gk5ben5vghljq6twm7lwmxla
    DATACITE_RELATED_ID = 'datacite_related_id'
    DATACITE_VERSION = 'datacite_version'
    DATASET_DOI = 'dataset_doi'
    DOI = 'doi'
    FIGSHARE_VERSION = 'figshare_version'
    JACCARD_AUTHORS = 'jaccard_authors'
    JSTOR_ID = 'jstor_id'
    MAX_CLUSTER_SIZE_EXCEEDED = 'max_cluster_size_exceeded'
    NUM_DIFF = 'num_diff'
    PAGE_COUNT = 'page_count'
    PMID_DOI_PAIR = 'pmid_doi_pair'
    PREPRINT_PUBLISHED = 'preprint_published'
    PUBLISHER_BLACKLIST = 'publisher_blacklist'
    RELEASE_TYPE = 'release_type'
    SHARED_DOI_PREFIX = 'shared_doi_prefix'
    SHORT_TITLE = 'short_title'
    SINGULAR_CLUSTER = 'singular_cluster'
    SLUG_TITLE_AUTHOR_MATCH = 'slug_title_author_match'
    SUBTITLE = 'subtitle'
    TITLE_ARTIFACT = 'title_artifact'
    TITLE_AUTHOR_MATCH = 'title_author_match'
    TITLE_FILENAME = 'title_filename'
    TOKENIZED_AUTHORS = 'tokenized_authors'
    UNKNOWN = 'unknown'
    VERSIONED_DOI = 'versioned_doi'
    WORK_ID = 'work_id'
    YEAR = 'year'
