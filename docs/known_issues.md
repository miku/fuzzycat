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
