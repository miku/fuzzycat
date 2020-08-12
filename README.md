# fcfuzzy

Fuzzy matching publications for [fatcat](https://fatcat.wiki).

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

