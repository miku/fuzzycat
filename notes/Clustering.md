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

# Verification

* we only need to look at identified duplicates, which will be a few millions
* we want fast access to all release JSON blob via ident, maybe do a
  "fuzzycat-cache" that copies relevant files into the fs, e.g.
"~/.cache/fuzzycat/releases/d9/e4d4be49faafc750563351a126e7bafe29.json or via microblob (but http we do not need), or sqlite3 (https://www.sqlite.org/fasterthanfs.html)

For verification we need to have the cached json blobs in some fast,
thread-safe store. Estimated: 1K/s accesses, we still would need a few hours
for a run.

* [ ] find all ids we need, generate cache, maybe reduce number of fields
* [ ] run verification on each cluster; generate a file of same format of
  "verified" clusters; take note the clustering and verification method

Overall, we can combine various clustering and verification methods. We can
also put together a list of maybe 100-200 test cases and evaluate methods.
