# Fixtures

Put all documents used as inputs and output here. The wiring can happen in
code or in separate file (for general editing).

## verify.csv

[This file](https://github.com/miku/fuzzycat/blob/master/tests/data/verify.csv)
currently contains four columns: two identifiers, a match status and an
optional reason.

If you add lines to this file, the test suite will pick it up automatically.

```csv
7kzrmoajzzedxgdvbltgqihszu,bd4crw4p7ber7pzhpoyw2c77bi,Status.STRONG,OK.SLUG_TITLE_AUTHOR_MATCH,
```

