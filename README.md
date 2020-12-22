# fuzzycat (wip)

Fuzzy matching utilities for [fatcat](https://fatcat.wiki).

![https://pypi.org/project/fuzzycat/](https://img.shields.io/pypi/v/fuzzycat?style=flat-square)

## Dataset

For development, we worked on a `release_export_expanded.json` dump (113G/700G
zstd/plain, XXX lines) and with the [fatcat API](https://api.fatcat.wiki/).

![](notes/steps.png)

## Facilities

### Clustering

Derive cluster of similar documents from a [fatcat database release
dump](https://archive.org/details/fatcat_snapshots_and_exports?&sort=-publicdate).

Following algorithms are implemented (or planned):

* [x] exact title matches (title)
* [x] normalized title matches (tnorm)
* [x] NYSIIS encoded title matches (tnysi)
* [x] extended title normalization (tsandcrawler)

Example running clustering:

```
$ python -m fuzzycat cluster -t tsandcrawler < data/re.json > cluster.json.zst
```

Clustering works in a three step process:

1. key extraction for each document (choose algorithm)
2. sorting by keys (via [GNU sort](https://www.gnu.org/software/coreutils/manual/html_node/sort-invocation.html))
3. group by key and write out ([itertools.groupby](https://docs.python.org/3/library/itertools.html#itertools.groupby))

### Verification

Run verification (pairwise *double-check* of match candidates in a cluster).

```
$ time zstdcat -T0 sample_cluster.json.zst | python -m fuzzycat verify > sample_verify.txt

real    7m56.713s
user    8m50.703s
sys     0m29.262s
```

This is a one-pass operation. For processing 150M docs, we very much depend on
the documents being on disk in a file (we keep the complete document in a
clustering doc).

Example results over 10M docs:



# A full run

Single threaded, 42h.

```
$ time zstdcat -T0 release_export_expanded.json.zst | \
    TMPDIR=/bigger/tmp python -m fuzzycat cluster --tmpdir /bigger/tmp -t tsandcrawler | \
    zstd -c9 > cluster_tsandcrawler.json.zst
{
  "key_fail": 0,
  "key_ok": 154202433,
  "key_empty": 942,
  "key_denylist": 0,
  "num_clusters": 124321361
}

real    2559m7.880s
user    2605m41.347s
sys     118m38.141s
```

So, 29881072 (about 20%) docs in the potentially duplicated set.

Verification (about 15h):

```
$ time zstdcat -T0 cluster_tsandcrawler.json.zst | python -m fuzzycat verify | \
    zstd -c9 > cluster_tsandcrawler_verified_3c7378.tsv.zst

...

real    927m28.631s
user    939m32.761s
sys     36m47.602s
```


# Use cases

* [ ] take a release entity database dump as JSON lines and cluster releases
  (according to various algorithms)
* [ ] take cluster information and run a verification step (misc algorithms)
* [ ] create a dataset that contains grouping of releases under works
* [ ] command line tools to generate cache keys, e.g. to match reference
  strings to release titles (this needs some transparent setup, e.g. filling of
a cache before ops)

# Usage

Release clusters start with release entities json lines.

```shell
$ cat data/sample.json | python -m fuzzycat cluster -t title > out.json
```

Clustering 1M records (single core) takes about 64s (15K docs/s).

```shell
$ head -1 out.json
{
  "k": "裏表紙",
  "v": [
    ...
  ]
}
```

Using GNU parallel to make it faster.

```
$ cat data/sample.json | parallel -j 8 --pipe --roundrobin python -m fuzzycat.main cluster -t title
```

Interestingly, the parallel variants detects fewer clusters (because data is
split and clusters are searched within each batch). TODO(miku): sort out sharding bug.


## QA

### 10M release dataset

Notes on cadd28a version clustering (nysiis) and verification.

* 10M docs
* 9040789 groups
* 665447 verification pairs

```
3578378 OK.TITLE_AUTHOR_MATCH
2989618 Miss.CONTRIB_INTERSECTION_EMPTY
2731528 OK.SLUG_TITLE_AUTHOR_MATCH
2654787 Miss.YEAR
2434532 OK.WORK_ID
2050468 OK.DUMMY
1619330 Miss.SHARED_DOI_PREFIX
1145571 Miss.BOOK_CHAPTER
1023925 Miss.DATASET_DOI
 934075 OK.DATACITE_RELATED_ID
 868951 OK.DATACITE_VERSION
 704154 OK.FIGSHARE_VERSION
 682784 Miss.RELEASE_TYPE
 607117 OK.TOKENIZED_AUTHORS
 298928 OK.PREPRINT_PUBLISHED
 270658 Miss.SUBTITLE
 227537 Miss.SHORT_TITLE
 196402 Miss.COMPONENT
 163158 Miss.CUSTOM_PREFIX_10_5860_CHOICE_REVIEW
 122614 Miss.CUSTOM_PREFIX_10_7916
  79687 OK.CUSTOM_IEEE_ARXIV
  69648 OK.PMID_DOI_PAIR
  46649 Miss.CUSTOM_PREFIX_10_14288
  38598 OK.CUSTOM_BSI_UNDATED
  15465 OK.DOI
  13393 Miss.CUSTOM_IOP_MA_PATTERN
  10378 Miss.CONTAINER
   3045 Miss.BLACKLISTED
   2504 Miss.BLACKLISTED_FRAGMENT
   1574 Miss.TITLE_FILENAME
   1273 Miss.APPENDIX
    104 Miss.NUM_DIFF
      4 OK.ARXIV_VERSION

```
