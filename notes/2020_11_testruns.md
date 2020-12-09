# Test runs

## Using --min-cluster-size

Skipping writes of single element clusters cuts clustering from ~42h to ~22h.

```
$ time zstdcat -T0 release_export_expanded.json.zst | \
    TMPDIR=/bigger/tmp python -m fuzzycat cluster --min-cluster-size 2 \
        --tmpdir /bigger/tmp -t tsandcrawler | \
    zstd -c9 > cluster_tsandcrawler_min_cluster_size_2.json.zst
...
max cluster size cut off for: 雜報その1
max cluster size cut off for: 雜録
2020-11-27 18:31:39.825 DEBUG __main__ - run_cluster: {"key_fail": 0, "key_ok":
154202433, "key_empty": 942, "key_denylist": 0, "num_clusters": 11763096}

real    1328m46.994s
user    1088m6.837s
sys     98m17.501s
```

We find 11763096 clusters, 16GB compressed (zstdcat takes about 5min,
sequential read at 50M/s).

```
$ time zstdcat -T0 cluster_tsandcrawler_min_cluster_size_2.json.zst | \
    python -m fuzzycat verify | \
    zstd -T0 -c9 > cluster_tsandcrawler_min_cluster_size_2_verify.tsv.zst
```

The cluster size distribution is:

```
9086522 2
1486742 3
 506125 4
 211335 5
 126678 6
  67592 7
  47085 8
  32587 9
  23975 10
  19153 11
  16318 12
  12167 100
  12051 13
  10345 14
   8687 15
   7418 16
   6655 17
   6451 18
   5233 19
   4865 20
    ...
```

Preliminary case distribution:

```
3578378 OK.TITLE_AUTHOR_MATCH
2989618 Miss.CONTRIB_INTERSECTION_EMPTY
2731528 OK.SLUG_TITLE_AUTHOR_MATCH
2654787 Miss.YEAR
2434532 OK.WORK_ID
2050468 OK.DUMMY
1619330 Miss.SHARED_DOI_PREFIX
1145571 Miss.BOOK_CHAPTER
1023925 Miss.DATASET_DOI
 934075 OK.DATACITE_RELATED_ID
 868951 OK.DATACITE_VERSION
 704154 OK.FIGSHARE_VERSION
 682784 Miss.RELEASE_TYPE
 607117 OK.TOKENIZED_AUTHORS
 298928 OK.PREPRINT_PUBLISHED
 270658 Miss.SUBTITLE
 227537 Miss.SHORT_TITLE
 196402 Miss.COMPONENT
 163158 Miss.CUSTOM_PREFIX_10_5860_CHOICE_REVIEW
 122614 Miss.CUSTOM_PREFIX_10_7916
  79687 OK.CUSTOM_IEEE_ARXIV
  69648 OK.PMID_DOI_PAIR
  46649 Miss.CUSTOM_PREFIX_10_14288
  38598 OK.CUSTOM_BSI_UNDATED
  15465 OK.DOI
  13393 Miss.CUSTOM_IOP_MA_PATTERN
  10378 Miss.CONTAINER
   3045 Miss.BLACKLISTED
   2504 Miss.BLACKLISTED_FRAGMENT
   1574 Miss.TITLE_FILENAME
   1273 Miss.APPENDIX
    104 Miss.NUM_DIFF
      4 OK.ARXIV_VERSION
```

## Case Mining

> "-" ignore, "x" done

* [-] https://fatcat.wiki/release/3jnis3ebrfgcdmdaa4aunc7xfi https://fatcat.wiki/release/wb3qvo27irfohmo3pa3aatpooa Status.AMBIGUOUS OK.DUMMY
* [-] https://fatcat.wiki/release/byrshkihwjfmplsv3ozbmpsz64 https://fatcat.wiki/release/fpll6q4ebvfgvonwi4vvetzjlq Status.AMBIGUOUS OK.DUMMY
* [x] https://fatcat.wiki/release/vqjpcuqxnbhdtelzspxjmklm7u https://fatcat.wiki/release/knuzh5bcqbg7ph7ffvqaiwevti Status.AMBIGUOUS OK.DUMMY
* [x] https://fatcat.wiki/release/psykbwxylndtdaand2ymtkgzqu https://fatcat.wiki/release/xizkwvsodzajnn4u7lgeldqoum Status.AMBIGUOUS OK.DUMMY

Added a stricter year check.

* [ ] https://fatcat.wiki/release/in2mm2wafbczjgzlapq55rrksq https://fatcat.wiki/release/oaezupjwnfckxaajjhjb3fl42e Status.AMBIGUOUS OK.DUMMY

Seems to be the same, but hard to confirm. Paywall.

* [ ] https://fatcat.wiki/release/u4mjilmo75bcnjyms564l66jea https://fatcat.wiki/release/6ofr4mqnmrdy3nyyh5ufm5ats4 Status.AMBIGUOUS OK.DUMMY

Great example; same, but sparse md.

* [ ] https://fatcat.wiki/release/2qcjbknhyrhh5dbuxobjy3gmqm https://fatcat.wiki/release/r6znetafszbuvaevbasn7ezsk4 Status.AMBIGUOUS OK.DUMMY

Two different reviews on the same book or article. A review is usually short (e.g. 1-2 pages only).

* [ ] https://fatcat.wiki/release/fidfj3g6ync2xdpkfcfdtf2jbu https://fatcat.wiki/release/rhu6ehpipbdofaijktvqypf5fe Status.AMBIGUOUS OK.DUMMY

BSI, but no "u" pattern.

* [x] https://fatcat.wiki/release/mz6a32xbp5f67i2cnbco2hmzj4 https://fatcat.wiki/release/fo5dsqeocfekfhqdzgqyng3z6q Status.AMBIGUOUS OK.DUMMY

One is a book, the other one is a review (choice review).

* [x] https://fatcat.wiki/release/g2swo5fewnhv3ihmlpl32sojr4 https://fatcat.wiki/release/ab2q56gokfdmzpccrmwfcdljgy Status.AMBIGUOUS OK.DUMMY

Choice review.

* [ ] https://fatcat.wiki/release/3w4tibll4rdernjrn4hkkyqsem https://fatcat.wiki/release/tmlg73royrdwdhl6nijf6m7vzy Status.AMBIGUOUS OK.DUMMY

Tow different reviews. md: one has an author, the other not.

* [ ] https://fatcat.wiki/release/kqlifv7lyjdmbfictjzaoixahm https://fatcat.wiki/release/54ilu5kdj5fktohbs5zybtfq7y Status.AMBIGUOUS OK.DUMMY

Defer.

* [ ] https://fatcat.wiki/release/7x7tszf54zggvp4xkrhakp667u https://fatcat.wiki/release/eqcgtpav3na5jh56o5vjsvb4ei Status.AMBIGUOUS OK.DUMMY

Same, pubmed id only and oxfordjournals doi, same year. New: `PMID_DOI_PAIR`

* [ ] https://fatcat.wiki/release/idpgijvcsnbqrgs2dg36vzzdzm https://fatcat.wiki/release/wm2p5fznwffknjx56lvmr7hn4q Status.AMBIGUOUS OK.DUMMY

* new: `SHARED_DOI_PREFIX`

* [ ] https://fatcat.wiki/release/nqcfu4il45aixekvk3rwflahdm https://fatcat.wiki/release/72uzveph65ce7kfdct2wpgh5j4 Status.AMBIGUOUS OK.DUMMY

Seems wo work.

* [ ] https://fatcat.wiki/release/zizw6bgxu5cnxfx5h3v7q7gute https://fatcat.wiki/release/jwh6xci4m5dktmea6bphhc3mjy Status.AMBIGUOUS OK.DUMMY

> choice review

* [ ] https://fatcat.wiki/release/b7bbygyawzdsthai7j7rmztrxe https://fatcat.wiki/release/mvvbim7kdffvtosuldtv5m3uy4 Status.AMBIGUOUS OK.DUMMY

Different.

* [ ] https://fatcat.wiki/release/dauh7n5w65enhk5zwdfwqxv344 https://fatcat.wiki/release/773m6wdunreqzlae6nts44rudy Status.AMBIGUOUS OK.DUMMY

Component (pdf, video)

* [ ] https://fatcat.wiki/release/voruupqxhvggfex4zlczcmjxxu https://fatcat.wiki/release/jg72qhdvmncfdfxg5l47hw3uba Status.AMBIGUOUS OK.DUMMY

Different, but apart from "chapter" vs "article-journal" nothing to use.

* [ ] https://fatcat.wiki/release/nc5qyc3umff5zevew2dobmispy https://fatcat.wiki/release/frdluoflhfgglphbotrazdyioq Status.AMBIGUOUS OK.DUMMY

> reference entries; probably an update of a "base" publication from 2012; paywalled

* [ ] https://fatcat.wiki/release/yq5m7zo3gfeivlrgpwy26znuva https://fatcat.wiki/release/zng4vgsqsnfejo55eixtkdqs5m Status.AMBIGUOUS OK.DUMMY

Two different editions (7th and 8th) - do we group editions under work? In FRBR
lingo, this might be a "derivative relationship" - so we should probably use
WEAK, DIFFERENT or AMBIGUOUS

* [ ] https://fatcat.wiki/release/yp3rs3xb5ra2riyx5xayrlqfum https://fatcat.wiki/release/6ysfa7ncx5fldmvmwvjgpf2i6e Status.AMBIGUOUS OK.DUMMY

OK.

* [ ] https://fatcat.wiki/release/arqtphat7fashokettncepu7xe https://fatcat.wiki/release/v6p7xct6kfgwtdbh57zfjqmuua Status.AMBIGUOUS OK.DUMMY

Ambiguous.

* [ ] https://fatcat.wiki/release/b3uhit7b4vhvliocdzwxr7peyy https://fatcat.wiki/release/zwru5ugcsfcyzeuqlygfw46vwq Status.AMBIGUOUS OK.DUMMY

A difficult prefix.

* [ ] https://fatcat.wiki/release/s7a4o5v5gfg4tbzna6poyg7nzy https://fatcat.wiki/release/tcro5wr6brhqnf5wettyiauw34 Status.AMBIGUOUS OK.DUMMY

BSI, one is a subdocument of another. The subdocument has a subtitle. That's more is-part-of.

* [ ] https://fatcat.wiki/release/b3odcrpuwveqljszl7l4c4ah5e https://fatcat.wiki/release/j4drpogsbzfd7esim4um5me374 Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/4owywaqwwvhrthytdjbulmltue https://fatcat.wiki/release/cy2v4wpm7nfptexi6ybjylapee Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/5ba6m23tmvcwdcpq3a2rcof4du https://fatcat.wiki/release/wczxyrrmovf3te5ziep7bbdreu Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/tksiqaqw3fb2rdiszgsal26lku https://fatcat.wiki/release/6kzbczpsxjhtjjz6x2srkp4rbe Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/wvgpq3vdd5hdrosg6nun2jobly https://fatcat.wiki/release/4dm7vmuv7fadxh5uumc3x4eal4 Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/n2agfjrbvjbxnocoobb7cofqzy https://fatcat.wiki/release/rbvztbywgfd3vpbelawvb7ulty Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/gncyo2gjrrbiphavmpbd7yix7y https://fatcat.wiki/release/olw7i5gmyjgfji3lk57mmo3rrm Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/owv47unlhjduhbnf6vftfe5364 https://fatcat.wiki/release/ig5cqwobgjgcforiq3zvxp4poq Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/ewgtefev5rcabisgixerg7aep4 https://fatcat.wiki/release/urtols4ovjg57k5do5kb7cg3ui Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/ocdgt5h5nzgc3pr3hledvlks7a https://fatcat.wiki/release/xcno2xuoc5eo7ajsvv7ol6zkpa Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/lghaypucrraevgpwqsauyc4vg4 https://fatcat.wiki/release/nusozx5eijd7hjpokzxot6duru Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/4rxft53u5rfd7orhfhkjgwu6ly https://fatcat.wiki/release/b2zqn4bjqrdyhdvdl2baivxf4i Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/ojk6vxg2krajbf5nr6klq4fmty https://fatcat.wiki/release/zq42eqmnfvdh7dmf774d4zwlx4 Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/3d73i34irjedjnhulyhmehnrvq https://fatcat.wiki/release/winjvljpu5al5deaz7v5qi7kta Status.AMBIGUOUS OK.DUMMY
* [ ] https://fatcat.wiki/release/jna6aodi2rfq7gwzxhb4s45kqy https://fatcat.wiki/release/3qst2qrdbvdhrdvu22kyqt22xy Status.AMBIGUOUS OK.DUMMY

