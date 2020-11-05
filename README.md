# fuzzycat (wip)

Fuzzy matching publications for [fatcat](https://fatcat.wiki).

* [fuzzycat](https://pypi.org/project/fuzzycat/)

Note: This is currently work-in-progress.

# Use cases

* [ ] take a release entity database dump as JSON lines and cluster releases
  (according to various algorithms)
* [ ] take cluster information and run a verification step (misc algorithms)

# Usage

Release clusters start with release entities json lines.

```shell
$ cat data/sample.json | python -m fuzzycat.main cluster -t title > out.json
```

Clustering 1M records (single core) takes about 64s (15K docs/s).

```shell
$ head -1 out.json
{
  "c": "release_key_title",
  "v": [
    "7ufkzsjywzejvjzsyegugradoa",
    "harjqexl5vagxc54zjfen5zlve",
    "i5jrdoxqmjfs3fk2dcpnqxqb2e",
    "i62bo63qqzggjjk7pf77z26djm",
    "omo3z5y7qvh6hbl7wjacinsfiq",
    "prkik3s5vzejnfe4u26g2vt2wu",
    "pyqss6ifnvgqjeqohlampswvkm",
    "spr2b23fk5asph7v6shrd6okt4",
    "togokylwfvcvzilhnx4jir2hfm",
    "us4artv2hbc5bljuwaopquicfu",
    "ycargjj4lzddnmyzbh2e22wsii"
  ],
  "k": "裏表紙"
}
```

Using GNU parallel to make it faster.

```
$ cat data/sample.json | parallel -j 8 --pipe --roundrobin python -m fuzzycat.main cluster -t title
```

Interestingly, the parallel variants detects fewer clusters (because data is
split and clusters are searched within each batch).


## Cluster

```shell
usage: fuzzycat command [options] cluster [-h] [--prefix PREFIX]
                                          [--tmpdir TMPDIR] [-P] [-f FILES]
                                          [-t TYPE]
                                          {cluster,verify} ...

positional arguments:
  {cluster,verify}
    cluster             group entities
    verify              verify groups

optional arguments:
  -h, --help            show this help message and exit
  --prefix PREFIX       temp file prefix
  --tmpdir TMPDIR       temporary directory
  -P, --profile         profile program
  -f FILES, --files FILES
                        output files
  -t TYPE, --type TYPE  cluster algorithm: title, tnorm, tnysi
```
