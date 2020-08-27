# OAI metadata matching

Goal: end-to-end data workflow (acquisition, harvest, matching, new release entities).

## Plan

* [ ] get JSON version, via [oai_harvest_20200215](https://archive.org/details/oai_harvest_20200215)
* [ ] filter out out of scope data
* [ ] (a) for items that have a doi, figure out, whether we already have md for this doi via API
* [ ] (b) for items w/o doi, get a list of (id, title)
* [ ] run fuzzy matching over title list to find out which one we have

## Get data

```
$ make
```

* compressed 12G, around 100G uncompressed

