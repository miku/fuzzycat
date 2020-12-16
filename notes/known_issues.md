# Known issues

Both the clustering and verification stage are not perfect. Here, some known
cases are documented.

# General observations

## One article included in different publications

A DOI prefix (10.1210, The Endocrine Society)  may choose to include the same
document in different publications:

* https://fatcat.wiki/release/52lwj4ip3nbdbgrgk4uwolbjt4
* https://fatcat.wiki/release/6tbrmc3pq5axzf3yhqayq256a4
* https://fatcat.wiki/release/457lzlw7czeo7aspcyttccvyrq

## Book or Dataset

Sometimes, a lexicon entry is a "dataset", sometimes a "book", e.g. "Unold, Max"

* https://fatcat.wiki/release/7ah6efvk2ncjzgywch2cmtfumq
* https://fatcat.wiki/release/nj7v4e3cxbfybozjmdiuwqo4sm

## Variation in authors

* https://fatcat.wiki/release/2kpa6ynwjzhtbbokqyxcl25gmm
* https://fatcat.wiki/release/o4dh7w7nqvdknm4j336yrom4wy

# Ideas for fixes

* [x] when title and authors match, check the year, and maybe the doi prefix;
  doi with the same prefix may not be duplicates
* [x] detect arxiv versions directly
* [ ] if multiple authors, may require more than one overlap, e.g. "by Yuting
  Yao, Yuting Yao, Yuting Yao, Imperial College London, Imperial College
London" - will overlap with any other author including "Imperial College
London" -- we label `OK.SLUG_TITLE_AUTHOR_MATCH`,
https://fatcat.wiki/release/6qbne2adybegdf6plgb7dnly2a,
https://fatcat.wiki/release/v6cjc6kxzncztebmfgzxwov7ym
* [ ] "article-journal" and "article" `release_type` should be treated the same, https://fatcat.wiki/release/k5zdpb45ufcy7grrppqndtxxji, https://fatcat.wiki/release/ypyse6ff4nbzrfd44resyav25m
* [x] if title and publisher matches, but DOI and year is different, assume
different, e.g. https://fatcat.wiki/release/k3hutukomngptcuwdys5omv2ty,
https://fatcat.wiki/release/xmkiqj4bizcwdaq5hljpglkzqe, or
https://fatcat.wiki/release/phuhxsj425fshp2jxfwlp5xnge and
https://fatcat.wiki/release/2ncazub5tngkjn5ncdk65jyr4u -- these might be repeatedly published
* [ ] article and "reply", https://pubmed.ncbi.nlm.nih.gov/5024865/, https://onlinelibrary.wiley.com/doi/abs/10.5694/j.1326-5377.1972.tb47249.x
* [ ] figshare uses versions, too, https://fatcat.wiki/release/zmivcpjvhba25ldkx27d24oefa, https://fatcat.wiki/release/mjapiqe2nzcy3fs3hriw253dye
* [ ] zenodo has no explicit versions, but ids might be closeby, e.g.
  https://fatcat.wiki/release/mbnr3nrdijerto6wfjnlsmfhga,
https://fatcat.wiki/release/mbnr3nrdijerto6wfjnlsmfhga

# Clustering

# Verification

## A new approach to fault-tolerant wormhole routing for mesh-connected parallel computers

* https://fatcat.wiki/release/izaz6gjnfzhgnaetizf4bt2r24
* https://fatcat.wiki/release/vwfepcqcdzfwjnsoym7o5o75yu

## Book-Chapter yields VERSIONED DOI

```
$ python -m fuzzycat verify-single | jq .
{
  "extra": {
    "q": "https://fatcat.wiki/release/search?q=Beardmore"
  },
  "a": "https://fatcat.wiki/release/zrkabzp4vjbwfdixvjkohgeh3a",
  "b": "https://fatcat.wiki/release/ojcucauvkvhg5cazfhzplcot7q",
  "r": [
    "strong",
    "versioned_doi"
  ]
}
```

* https://fatcat.wiki/release/zrkabzp4vjbwfdixvjkohgeh3a (book)
* https://fatcat.wiki/release/ojcucauvkvhg5cazfhzplcot7q (chapter)

## Tokenized authors is flaky

```
$ python -m fuzzycat verify_single | jq .
{
  "extra": {
    "q": "https://fatcat.wiki/release/search?q=cleaves"
  },
  "a": "https://fatcat.wiki/release/mi6y2jtl55egxi5qfhovswxcba",
  "b": "https://fatcat.wiki/release/7hjisijl7nczhbghdd6l56n6py",
  "r": [
    "strong",
    "tokenized_authors"
  ]
}
```
