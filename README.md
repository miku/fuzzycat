# fuzzycat (wip)

Fuzzy matching publications for [fatcat](https://fatcat.wiki).

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
  "miss.blacklisted": 12124,
  "miss.blacklisted_fragment": 9,
  "miss.book_chapter": 46733,
  "miss.component": 2173,
  "miss.contrib_intersection_empty": 73592,
  "miss.dataset_doi": 30806,
  "miss.num_diff": 1,
  "miss.release_type": 19767,
  "miss.short_title": 16737,
  "miss.subtitle": 11975,
  "miss.title_filename": 87,
  "miss.year": 123288,
  "ok.arxiv_version": 90726,
  "ok.dummy": 106196,
  "ok.preprint_published": 10495,
  "ok.slug_title_author_match": 47285,
  "ok.title_author_match": 65685,
  "ok.tokenized_authors": 7592,
  "skip.container_name_blacklist": 20,
  "skip.publisher_blacklist": 456,
  "skip.too_large": 7430,
  "skip.unique": 8808462,
  "total": 9481815
}
```

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

#### Cases

* common title, "Books by Our Readers", https://fatcat.wiki/release/4uv5jsy5vnhdvnxvzmucqlksvq, https://fatcat.wiki/release/4uv5jsy5vnhdvnxvzmucqlksvq
* common title, "The Future of Imprisonment"
* common title, "In This Issue/Research Watch/News-in-Brief/News from the IASLC Tobacco Control Committee"
* common title, "IEEE Transactions on Wireless Communications", same publisher, different year
* common title, "ASMS News" (also different year)
* common title, "AMERICAN INSTITUTE OF INSTRUCTION"
* common title, "Contents lists"
* common title, "Submissions"
* same, except DOI, but maybe the same item, after all? https://fatcat.wiki/release/kxgsbh66v5bwhobcaiuh4i7dwy, https://fatcat.wiki/release/thl7o44z3jgk3njdypixwrdbve

Authors may be messy:

* IR and published, be we currently yield `Miss.CONTRIB_INTERSECTION_EMPTY` -
  https://fatcat.wiki/release/2kpa6ynwjzhtbbokqyxcl25gmm,
https://fatcat.wiki/release/o4dh7w7nqvdknm4j336yrom4wy - may need to tokenize authors

A DOI prefix (10.1210, The Endocrine Society)  may choose to include the same
document in different publications:

* https://fatcat.wiki/release/52lwj4ip3nbdbgrgk4uwolbjt4
* https://fatcat.wiki/release/6tbrmc3pq5axzf3yhqayq256a4
* https://fatcat.wiki/release/457lzlw7czeo7aspcyttccvyrq

Sometimes, a lexicon entry is a "dataset", sometimes a "book", e.g.:

* https://fatcat.wiki/release/7ah6efvk2ncjzgywch2cmtfumq
* https://fatcat.wiki/release/nj7v4e3cxbfybozjmdiuwqo4sm

#### Possible fixes

* [ ] when title and authors match, check the year, and maybe the doi prefix; doi with the same prefix may not be duplicates
* [x] detect arxiv versions directly
* [ ] if multiple authors, may require more than one overlap, e.g. "by Yuting
  Yao, Yuting Yao, Yuting Yao, Imperial College London, Imperial College
London" - will overlap with any other author including "Imperial College
London" -- we label `OK.SLUG_TITLE_AUTHOR_MATCH`,
https://fatcat.wiki/release/6qbne2adybegdf6plgb7dnly2a,
https://fatcat.wiki/release/v6cjc6kxzncztebmfgzxwov7ym
* [ ] "article-journal" and "article" `release_type` should be treated the same, https://fatcat.wiki/release/k5zdpb45ufcy7grrppqndtxxji, https://fatcat.wiki/release/ypyse6ff4nbzrfd44resyav25m
* [ ] if title and publisher matches, but DOI and year is different, assume
different, e.g. https://fatcat.wiki/release/k3hutukomngptcuwdys5omv2ty,
https://fatcat.wiki/release/xmkiqj4bizcwdaq5hljpglkzqe, or
https://fatcat.wiki/release/phuhxsj425fshp2jxfwlp5xnge and
https://fatcat.wiki/release/2ncazub5tngkjn5ncdk65jyr4u -- these might be repeatedly published
* [ ] article and "reply", https://pubmed.ncbi.nlm.nih.gov/5024865/, https://onlinelibrary.wiley.com/doi/abs/10.5694/j.1326-5377.1972.tb47249.x
* [ ] figshare uses versions, too, https://fatcat.wiki/release/zmivcpjvhba25ldkx27d24oefa, https://fatcat.wiki/release/mjapiqe2nzcy3fs3hriw253dye
* [ ] zenodo has no explicit versions, but ids might be closeby, e.g. https://fatcat.wiki/release/mbnr3nrdijerto6wfjnlsmfhga, https://fatcat.wiki/release/mbnr3nrdijerto6wfjnlsmfhga

#### 100 examples

* accuracy at around 0.8
* while the results look ok, the reasons are not always the ones that stand out
  the most (while checking manually)

```
78 [x]
11 [o]
11 [ ]
```

Ok cases are now in [verify.csv](https://github.com/miku/fuzzycat/blob/master/tests/data/verify.csv).

* [ ] https://fatcat.wiki/release/i2ziaqjrovh3rfrojcaf2xqidy https://fatcat.wiki/release/4rbsv4kplnf4tny22px5z35vty Status.DIFFERENT Miss.CONTRIB_INTERSECTION_EMPTY
* [o] https://fatcat.wiki/release/65qk35lrxfbqxnpjfpra3ankxe https://fatcat.wiki/release/tovzgangzbfm5bc2qriyh2k6da Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/qvlzvflp6vhojdm3uyvj2d6keq https://fatcat.wiki/release/vynqlyi2xjdexmf54a5yfidx6m Status.DIFFERENT Miss.RELEASE_TYPE
* [o] https://fatcat.wiki/release/hfewgpty4ne3zn7rg32z5npdxy https://fatcat.wiki/release/3djtma4xrjh2pcxy4gu6pafqji Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/ybxygpeypbaq5pfrztu3z2itw4 https://fatcat.wiki/release/2c2ztrtlkzdhfmzpf7fbindpjq Status.DIFFERENT Miss.DATASET_DOI
* [o] https://fatcat.wiki/release/eyol2bjf6jawhjnote73ej5v24 https://fatcat.wiki/release/jowohxiuuncqbdidvqjrrb5324 Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/d5bqydkylzelpmdfcks2v5th7q https://fatcat.wiki/release/lzcgl52npjaf3etfhhnb3d46da Status.DIFFERENT Miss.DATASET_DOI
* [o] https://fatcat.wiki/release/5ysvoxjj4jcxbji42nnzapr6n4 https://fatcat.wiki/release/dx6wevs345cjfejokze2te6sia Status.AMBIGUOUS OK.DUMMY
* [o] https://fatcat.wiki/release/xdclbyjgjnbehchrl7l2vi3274 https://fatcat.wiki/release/t3kqh6lfprfaff5zovh6qlodxy Status.AMBIGUOUS OK.DUMMY
* [o] https://fatcat.wiki/release/aogvyiw67vdsnf26bufauy2rqa https://fatcat.wiki/release/aofedljjhbhajmx5doxfcv43fa Status.AMBIGUOUS OK.DUMMY
* [o] https://fatcat.wiki/release/cjal2f6k5zesxcnrnyhc6ftg5e https://fatcat.wiki/release/oi5kzjlku5gpxjc247v6zjzosa Status.AMBIGUOUS OK.DUMMY
* [o] https://fatcat.wiki/release/o6e6yf37y5bttbrpo4piska4gq https://fatcat.wiki/release/pchjd5fwqjdqfevphjff7ydeae Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/l4fyyvsckneuxkq7d3y2zvkvbe https://fatcat.wiki/release/gf5hriyvuvarhcvttnooaffksi Status.DIFFERENT Miss.RELEASE_TYPE
* [ ] https://fatcat.wiki/release/7nbcgsohrrak5cuyk6dnit6ega https://fatcat.wiki/release/q66xv7drk5fnph7enwwlkyuwqm Status.DIFFERENT Miss.CONTRIB_INTERSECTION_EMPTY
* [ ] https://fatcat.wiki/release/2tzvdvx4t5hfxnqlnyt4rqenly https://fatcat.wiki/release/houszjo2ejbjhljxvxz23whgua Status.DIFFERENT Miss.DATASET_DOI
* [ ] https://fatcat.wiki/release/qsxbwvreu5ehrbz65ngh2ghcra https://fatcat.wiki/release/xjvo37ynxvc3zm55bxoa545gvq Status.EXACT OK.TITLE_AUTHOR_MATCH
* [ ] https://fatcat.wiki/release/ggzzwt6deneyrna5h65mvv7sfe https://fatcat.wiki/release/h4rnaxua75dndmq4x4snnw3qxe Status.AMBIGUOUS Miss.SHORT_TITLE
* [ ] https://fatcat.wiki/release/skxiyp7qmraqhe2o4zvo7iq6sq https://fatcat.wiki/release/qyqre3mzgbha7hhfarn5absqnq Status.EXACT OK.TITLE_AUTHOR_MATCH
* [o] https://fatcat.wiki/release/am53f7iyyvcjnjsgjbz7pu7dii https://fatcat.wiki/release/kdubht33hfb4dmghm2g27ck24i Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/ofmeeajuovbqbhkgh4rujkd3xu https://fatcat.wiki/release/r6bvy6cglfe5xgafvdcokawkue Status.DIFFERENT Miss.RELEASE_TYPE
* [o] https://fatcat.wiki/release/lezvxt2oong6xm3e3cgp47wsla https://fatcat.wiki/release/aad6r5am6vfxpbfwycmyudp2qe Status.AMBIGUOUS OK.DUMMY
* [o] https://fatcat.wiki/release/5mzzswgebze2tk4apmbwjahp34 https://fatcat.wiki/release/vl7r3uewvvbo5i2gntocy3y2ey Status.AMBIGUOUS OK.DUMMY


