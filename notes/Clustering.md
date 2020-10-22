# Clustering

Original dataset:

```
$ sha1sum release_export_expanded.json.zst
fa7ce335e27bbf6ccee227992ecd9b860e8e36af  release_export_expanded.json.zst

$ zstdcat -T0 release_export_expanded.json.zst | wc -l
```

Various clusters (title, title normalized, title nysiis (New York State
Identification and Intelligence System, ...):

```
$ zstdcat -T0 release_export_expanded.json.zst | fuzzycat-cluster -t title > cluster_title.json
```

Parallel:

```
$ zstdcat -T0 release_export_expanded.json.zst | \
    parallel --tmpdir /bigger/tmp --roundrobin --pipe -j 16 \
    fuzzycat-cluster --tmpdir /bigger/tmp -t title > cluster_title.json
```

Numbers of clusters:

```
  141022216 cluster_title.json
  134709771 cluster_title_normalized.json
  119829458 cluster_title_nysiis.json
```

# TODO

* [ ] do a SS like clustering, using title and author ngrams
* [ ] cluster by doi without "vX" suffix
