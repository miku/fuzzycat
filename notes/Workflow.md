# Workflow

Separate problem in half, first find clusters, then examine clusters (as
proposed).

## Finding clusters

* group by raw exact title
* group by lowercase title
* group by slug title
* group by ngram title and authors
* group by ngram title (prefix, suffix) and authors
* group by elasticsearch
* group by doi without vX prefix
* group by soundex
* group by a simhash over the record

As for performance, the feature needs to be calculated in one pass, then the
grouping reduces to a sort, in a second pass.

The output could be a TSV file, with method and then release identifiers.

```
rawt o3utonw5qzhddo7l4lmwptgeey nnpmnwln7be2zb5hd2qanq3r7q
```

Or jsonlines for a bit of structure.

```
{"m": "rawt", "c": ["o3utonw5qzhddo7l4lmwptgeey", "nnpmnwln7be2zb5hd2qanq3r7q"]}
```

```
$ zstdcat -T0 release_export_expanded.json.zst | fuzzycat-cluster -g > clusters.json
```

### Performance considerations

* [orjson](https://github.com/ijl/orjson), [pysimdjson](https://github.com/TkTech/pysimdjson)


## Examine cluster

There will be various methods by which to examine the cluster as well.

We need to fetch releases by identifier, this can be the full record or some
partial record that has been cached somewhere.

The input is then a list of releases and the output would be a equally sized or
smaller cluster of releases which we assume represent the same record.

Apart from that, there may be different relations, e.g. not the exact same
thing, but something, that has an interval to it, like some thing that mostly
differs in year?
