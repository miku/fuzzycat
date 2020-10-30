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

Parallel (TODO: use `--pipepart`):

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

The number of duplicate record goes up as number of clusters go down:

```
   2858088 cluster_title_dups.json
   5818143 cluster_title_normalized_dups.json
   6274940 cluster_title_nysiis_dups.json
```

# Cluster numbers

Using normalized title as example:

* 4306860 have cluster size 2, 1511283 have cluster size 3 or larger

```
             size         len
count 5818143.000 5818143.000
mean        4.350      52.120
std       196.347      35.026
min         2.000       0.000
25%         2.000      24.000
50%         2.000      46.000
75%         3.000      72.000
max    151383.000   11686.000
```

Around 448170 clusters with size 5 or more (with some example titles):

```
Medical Notes
日本鉄鋼協会第97回講演大会講演概要
Boutades
Allergic Contact Dermatitis
Comité international
Incontinence
Efficient Uncertainty Minimization for Fuzzy Spectral Clustering
Early Intervention
CURRENT READINGS IN NUCLEAR MEDICINE
Nannocystis exedens
```

Grouping. API, hide.

* gnu parallel; top, htop; how much; "chunks"; read one line; "pipeart";
  batching; "read from a file"; scan a file; "chunking"

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
