# TODO

* [ ] clustering should be broken up, e.g. into "map" and "sort"

In
[refcat/skate](https://gitlab.com/internetarchive/refcat/-/tree/master/skate)
we have one simple operation: extract a list of fields from blob of bytes. We
use [16
mappers](https://gitlab.com/internetarchive/refcat/-/blob/f33e586d11f5f575f71ad209608ac9ba74fad2e5/skate/cmd/skate-map/main.go#L70-86)
currently, they are easy to write.

In refcat, we use GNU sort, and just when we need it, e.g.
[skate-map](https://gitlab.com/internetarchive/refcat/-/blob/f33e586d11f5f575f71ad209608ac9ba74fad2e5/python/refcat/tasks.py#L531-534).

The `Cluster` class bundles, iteration, key extraction, sorting and group by
operation into a single entity.

Also in refcat, we do not work on a single file with clusters any more, but
mostly with two sorted streams, which are iterated over "comm" style. This
spares us an extra step of generating the cluster documents, but requires an
extra component, that allows to plug in various "reduce" functions. In refcat,
this component is called "zipkey", which is support batching, too.

* [ ] match release fuzzy should work not just with title
* [ ] match container name functions (maybe also with abbreviations, etc)
* [ ] better documentation, more examples
* [ ] shiv based packaging

