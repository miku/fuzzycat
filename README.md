# fuzzycat (wip)

Fuzzy matching publications for [fatcat](https://fatcat.wiki).

* [fuzzycat](https://pypi.org/project/fuzzycat/)

## Motivation

Most of the results on sites like [Google
Scholar](https://scholar.google.com/scholar?q=fuzzy+matching) group
publications into clusters. Each cluster represents one publication, abstracted
from its concrete representation as a link to a PDF.

We call the abstract publication *work* and the concrete instance a *release*.
The goal is to group releases under works and to implement a versions feature.

This repository contains both generic code for matching as well as fatcat
specific code using the fatcat openapi client.

## Datasets

* release and container metadata from: [https://archive.org/details/fatcat_bulk_exports_2020-08-05](https://archive.org/details/fatcat_bulk_exports_2020-08-05).
* issn journal level data, via [issnlister](https://github.com/miku/issnlister)
* abbreviation lists

## Matching approaches

![](static/approach.png)

## Performance data point

Candidate generation via elasticsearch, 40 parallel queries, sustained speed at
about 17857 queries per hour, that is around 5 queries/s.

```
$ time cat ~/data/researchgate/x04 | \
    parallel -j40 --pipe -N 1 ./fatcatx_rg_unmatched.py - \
    > ~/data/researchgate/x04_results.ndj
...
real    3409m16.442s
user    29177m5.516s
sys     4927m3.277s
```

## Data issues

### A republised article

* [https://fatcat.wiki/release/search?q=%22The+doctor+with+seven+billion+patients%22](https://fatcat.wiki/release/search?q=%22The+doctor+with+seven+billion+patients%22)

There is "student BMJ" and "BMJ" - this (html) article (interview) has been
first published on "sbmj" (Published 07 July 2011), then "bmj" (Published 10
August 2011).

> Notes; Originally published as: Student BMJ 2011;19:d3983

* https://www.bmj.com/content/343/sbmj.d3983
* https://www.bmj.com/content/343/bmj.d4964

It is essentially the same text, same title, author, just different DOI and
probably a different recorded date.

Generic pattern "republication" duplicate:

* metadata mostly same, except date and doi
