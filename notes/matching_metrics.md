# Matching Metrics

## Precision/Recall

For fuzzy matching we want to understand precision and recall. Options for test datasets:

* manually curated (100s of examples); could determine
* autogenerate slightly different set of real-world metadata (e.g. crossref vs. doaj) converted to releases
* automatically distorted set of records; 1 original, plus N distorted (synthetic)

## Overall numbers

* number of clusters per clustering method: "title", "lowercase", "nysiis",
  "sandcrawler", a few more - contrastive comparison of these cluster, e.g. how
many more matches/non-matches we get for the various methods
* take N docs from non-clusters and run verify; we would want 100% different/ambiguous results
