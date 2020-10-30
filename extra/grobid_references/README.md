# Grobid refs

References extracted from [grobid](https://grobid.readthedocs.io).

## TODO

* For a given reference string in grobid, find a matching release in fatcat.

## Approach

Two general ways:

* do queries against elasticsearch, which would max out at a few hundred queries/s
* offline compute a key (e.g. title, title ngram plus authors, etc.); then do comparisons

## Misc

Example grobid outputs:

* [grobid.tei.xml](grobid.tei.xml),
  [pdf](http://dss.in.tum.de/files/brandt-research/me.pdf) -- here grobid does
not extract many refs; GS looks ok
* [pdf](https://ia803202.us.archive.org/21/items/jstor-1064270/1064270.pdf)

