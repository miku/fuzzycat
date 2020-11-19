# fuzzycat (wip)

Fuzzy matching publications for [fatcat](https://fatcat.wiki).

* [fuzzycat](https://pypi.org/project/fuzzycat/)

Note: This is currently work-in-progress.

# Example Run

Run any clustering algorithm.

```
$ time python -m fuzzycat cluster -t tsandcrawler < data/sample10m.json | \
    zstd -c9 > sample_cluster.json.zst
2020-11-18 00:19:48.194 DEBUG __main__ - run_cluster:
    {"key_fail": 0, "key_ok": 9999938, "key_empty": 62, "key_denylist": 0, "num_clusters": 9040789}

real    75m23.045s
user    95m14.455s
sys     3m39.121s
```

Run verification.

```
$ time zstdcat -T0 sample_cluster.json.zst | python -m fuzzycat verify > sample_verify.txt

real    7m56.713s
user    8m50.703s
sys     0m29.262s
```


Example results over 10M docs:

```json
{
  "miss.appendix": 176,
  "miss.arxiv_version": 25,
  "miss.blacklisted": 12082,
  "miss.blacklisted_fragment": 5,
  "miss.book_chapter": 46733,
  "miss.component": 1567,
  "miss.contrib_intersection_empty": 47691,
  "miss.dataset_doi": 30806,
  "miss.num_diff": 1,
  "miss.release_type": 157718,
  "miss.short_title": 16263,
  "miss.subtitle": 6013,
  "miss.title_filename": 57,
  "miss.year": 148755,
  "ok.arxiv_version": 93,
  "ok.dummy": 88294,
  "ok.preprint_published": 110,
  "ok.slug_title_author_match": 15818,
  "ok.title_author_match": 93240,
  "skip.container_name_blacklist": 20,
  "skip.publisher_blacklist": 456,
  "skip.too_large": 7430,
  "skip.unique": 8808462,
  "total": 9481815
}
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
    176 Miss.APPENDIX
     25 Miss.ARXIV_VERSION
  12082 Miss.BLACKLISTED
      5 Miss.BLACKLISTED_FRAGMENT
  46733 Miss.BOOK_CHAPTER
   1567 Miss.COMPONENT
  47691 Miss.CONTRIB_INTERSECTION_EMPTY
  30806 Miss.DATASET_DOI
      1 Miss.NUM_DIFF
 157718 Miss.RELEASE_TYPE
  16263 Miss.SHORT_TITLE
   6013 Miss.SUBTITLE
     57 Miss.TITLE_FILENAME
 148755 Miss.YEAR
     93 OK.ARXIV_VERSION
  88294 OK.DUMMY
    110 OK.PREPRINT_PUBLISHED
  15818 OK.SLUG_TITLE_AUTHOR_MATCH
  93240 OK.TITLE_AUTHOR_MATCH
```

Cases

* common title, "Books by Our Readers", https://fatcat.wiki/release/4uv5jsy5vnhdvnxvzmucqlksvq, https://fatcat.wiki/release/4uv5jsy5vnhdvnxvzmucqlksvq
* common title, "The Future of Imprisonment"
* same title "IEEE Transactions on Wireless Communications", same publisher, different year
* same, except DOI, but maybe the same item, after all? https://fatcat.wiki/release/kxgsbh66v5bwhobcaiuh4i7dwy, https://fatcat.wiki/release/thl7o44z3jgk3njdypixwrdbve

Possible improvements:

* when title and authors match, check the year, and maybe the doi prefix; doi with the same prefix may not be duplicates
