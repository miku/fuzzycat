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

## Helpers

Going from a query to the combination of idents (with
[esdump](https://github.com/miku/esdump), [jq](https://stedolan.github.io/jq/),
[makecomb.py](https://gist.github.com/miku/c1220715060babc2374a440bd742a410):

```
$ esdump -q '"Calcifying+extracellular+mucus+substances"' | \
    jq -rC '.hits.hits[]._id' | makecomb.py | awk '{print $1","$2}'

5lk635o65nc2tnkus3pkf2ggeq,hqrvhbvocvaabg6nr5p43tl3uq
5lk635o65nc2tnkus3pkf2ggeq,zfwf3tefajc6zdxa47vgilm7wm
hqrvhbvocvaabg6nr5p43tl3uq,zfwf3tefajc6zdxa47vgilm7wm
```

Where `makecomb.py` turns lines into pairs.

```
$ curl -sL https://git.io/JkDwC > ~/bin/makecomb.py && chmod +x ~/bin/makecomb.py
```

Short script.

```python
#!/usr/bin/env python
import fileinput
import itertools

vs = set()
for line in fileinput.input():
    line = line.strip()
    if not line:
        continue
    vs.add(line)

for a, b in itertools.combinations(sorted(vs), r=2):
    print("{}\t{}".format(a, b))
```
