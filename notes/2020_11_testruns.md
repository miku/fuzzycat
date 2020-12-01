# Test runs

## Using --min-cluster-size

Skipping writes of single element clusters cuts clustering from ~42h to ~22h.

```
$ time zstdcat -T0 release_export_expanded.json.zst | \
    TMPDIR=/bigger/tmp python -m fuzzycat cluster --min-cluster-size 2 \
        --tmpdir /bigger/tmp -t tsandcrawler | \
    zstd -c9 > cluster_tsandcrawler_min_cluster_size_2.json.zst
...
max cluster size cut off for: 雜報その1
max cluster size cut off for: 雜録
2020-11-27 18:31:39.825 DEBUG __main__ - run_cluster: {"key_fail": 0, "key_ok":
154202433, "key_empty": 942, "key_denylist": 0, "num_clusters": 11763096}

real    1328m46.994s
user    1088m6.837s
sys     98m17.501s
```

We find 11763096 clusters, 16GB compressed (zstdcat takes about 5min,
sequential read at 50M/s).

```
$ time zstdcat -T0 cluster_tsandcrawler_min_cluster_size_2.json.zst | \
    python -m fuzzycat verify | \
    zstd -T0 -c9 > cluster_tsandcrawler_min_cluster_size_2_verify.tsv.zst
```

The cluster size distribution is:

```
9086522 2
1486742 3
 506125 4
 211335 5
 126678 6
  67592 7
  47085 8
  32587 9
  23975 10
  19153 11
  16318 12
  12167 100
  12051 13
  10345 14
   8687 15
   7418 16
   6655 17
   6451 18
   5233 19
   4865 20
    ...
```

Preliminary case distribution:

```
4053975 Miss.CONTRIB_INTERSECTION_EMPTY
4049590 OK.TITLE_AUTHOR_MATCH
3429950 OK.SLUG_TITLE_AUTHOR_MATCH
3427456 OK.DUMMY
2590271 Miss.YEAR
1402770 OK.ARXIV_VERSION
1145571 Miss.BOOK_CHAPTER
1134644 Miss.DATASET_DOI
 968751 OK.DATACITE_RELATED_ID
 906387 OK.FIGSHARE_VERSION
 786887 OK.TOKENIZED_AUTHORS
 687558 Miss.RELEASE_TYPE
 273600 Miss.SUBTITLE
 268129 OK.PREPRINT_PUBLISHED
 242075 Miss.SHORT_TITLE
 196402 Miss.COMPONENT
  15465 OK.DOI
   3045 Miss.BLACKLISTED
   1605 Miss.TITLE_FILENAME
   1318 Miss.BLACKLISTED_FRAGMENT
   1301 Miss.APPENDIX
     87 Miss.NUM_DIFF
```
