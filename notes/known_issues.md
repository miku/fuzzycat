# Known issues

Both the clustering and verification stage are not perfect. Here, some known
cases are documented.

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
