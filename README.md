# fuzzycat (wip)

Fuzzy matching publications for [fatcat](https://fatcat.wiki).

# Example Run

Run any clustering algorithm.

```
$ time python -m fuzzycat cluster -t tsandcrawler < data/sample10m.json | \
    zstd -c9 > sample_cluster.json.zst
2020-11-18 00:19:48.194 DEBUG __main__ - run_cluster:
    {"key_fail": 0, "key_ok": 9999938, "key_empty": 62, "key_denylist": 0, "num_clusters": 9040789}

real    75m23.045s
user    95m14.455s
sys     3m39.121s
```

Run verification.

```
$ time zstdcat -T0 sample_cluster.json.zst | python -m fuzzycat verify > sample_verify.txt

real    7m56.713s
user    8m50.703s
sys     0m29.262s
```


Example results over 10M docs:

```json
{
  "miss.appendix": 176,
  "miss.blacklisted": 12124,
  "miss.blacklisted_fragment": 9,
  "miss.book_chapter": 46733,
  "miss.component": 2173,
  "miss.contrib_intersection_empty": 73592,
  "miss.dataset_doi": 30806,
  "miss.num_diff": 1,
  "miss.release_type": 19767,
  "miss.short_title": 16737,
  "miss.subtitle": 11975,
  "miss.title_filename": 87,
  "miss.year": 123288,
  "ok.arxiv_version": 90726,
  "ok.dummy": 106196,
  "ok.preprint_published": 10495,
  "ok.slug_title_author_match": 47285,
  "ok.title_author_match": 65685,
  "ok.tokenized_authors": 7592,
  "skip.container_name_blacklist": 20,
  "skip.publisher_blacklist": 456,
  "skip.too_large": 7430,
  "skip.unique": 8808462,
  "total": 9481815
}
```


# Use cases

* [ ] take a release entity database dump as JSON lines and cluster releases
  (according to various algorithms)
* [ ] take cluster information and run a verification step (misc algorithms)
* [ ] create a dataset that contains grouping of releases under works
* [ ] command line tools to generate cache keys, e.g. to match reference
  strings to release titles (this needs some transparent setup, e.g. filling of
a cache before ops)

# Usage

Release clusters start with release entities json lines.

```shell
$ cat data/sample.json | python -m fuzzycat cluster -t title > out.json
```

Clustering 1M records (single core) takes about 64s (15K docs/s).

```shell
$ head -1 out.json
{
  "k": "裏表紙",
  "v": [
    ...
  ]
}
```

Using GNU parallel to make it faster.

```
$ cat data/sample.json | parallel -j 8 --pipe --roundrobin python -m fuzzycat.main cluster -t title
```

Interestingly, the parallel variants detects fewer clusters (because data is
split and clusters are searched within each batch). TODO(miku): sort out sharding bug.


## QA

### 10M release dataset

Notes on cadd28a version clustering (nysiis) and verification.

* 10M docs
* 9040789 groups
* 665447 verification pairs

```
    176 Miss.APPENDIX
     25 Miss.ARXIV_VERSION
  12082 Miss.BLACKLISTED
      5 Miss.BLACKLISTED_FRAGMENT
  46733 Miss.BOOK_CHAPTER
   1567 Miss.COMPONENT
  47691 Miss.CONTRIB_INTERSECTION_EMPTY
  30806 Miss.DATASET_DOI
      1 Miss.NUM_DIFF
 157718 Miss.RELEASE_TYPE
  16263 Miss.SHORT_TITLE
   6013 Miss.SUBTITLE
     57 Miss.TITLE_FILENAME
 148755 Miss.YEAR
     93 OK.ARXIV_VERSION
  88294 OK.DUMMY
    110 OK.PREPRINT_PUBLISHED
  15818 OK.SLUG_TITLE_AUTHOR_MATCH
  93240 OK.TITLE_AUTHOR_MATCH
```

#### Cases

* common title, "Books by Our Readers", https://fatcat.wiki/release/4uv5jsy5vnhdvnxvzmucqlksvq, https://fatcat.wiki/release/4uv5jsy5vnhdvnxvzmucqlksvq
* common title, "The Future of Imprisonment"
* common title, "In This Issue/Research Watch/News-in-Brief/News from the IASLC Tobacco Control Committee"
* common title, "IEEE Transactions on Wireless Communications", same publisher, different year
* common title, "ASMS News" (also different year)
* common title, "AMERICAN INSTITUTE OF INSTRUCTION"
* common title, "Contents lists"
* common title, "Submissions"
* same, except DOI, but maybe the same item, after all? https://fatcat.wiki/release/kxgsbh66v5bwhobcaiuh4i7dwy, https://fatcat.wiki/release/thl7o44z3jgk3njdypixwrdbve

Authors may be messy:

* IR and published, be we currently yield `Miss.CONTRIB_INTERSECTION_EMPTY` -
  https://fatcat.wiki/release/2kpa6ynwjzhtbbokqyxcl25gmm,
https://fatcat.wiki/release/o4dh7w7nqvdknm4j336yrom4wy - may need to tokenize authors

A DOI prefix (10.1210, The Endocrine Society)  may choose to include the same
document in different publications:

* https://fatcat.wiki/release/52lwj4ip3nbdbgrgk4uwolbjt4
* https://fatcat.wiki/release/6tbrmc3pq5axzf3yhqayq256a4
* https://fatcat.wiki/release/457lzlw7czeo7aspcyttccvyrq

Sometimes, a lexicon entry is a "dataset", sometimes a "book", e.g.:

* https://fatcat.wiki/release/7ah6efvk2ncjzgywch2cmtfumq
* https://fatcat.wiki/release/nj7v4e3cxbfybozjmdiuwqo4sm

#### Possible fixes

* [ ] when title and authors match, check the year, and maybe the doi prefix; doi with the same prefix may not be duplicates
* [x] detect arxiv versions directly
* [ ] if multiple authors, may require more than one overlap, e.g. "by Yuting
  Yao, Yuting Yao, Yuting Yao, Imperial College London, Imperial College
London" - will overlap with any other author including "Imperial College
London" -- we label `OK.SLUG_TITLE_AUTHOR_MATCH`,
https://fatcat.wiki/release/6qbne2adybegdf6plgb7dnly2a,
https://fatcat.wiki/release/v6cjc6kxzncztebmfgzxwov7ym
* [ ] "article-journal" and "article" `release_type` should be treated the same, https://fatcat.wiki/release/k5zdpb45ufcy7grrppqndtxxji, https://fatcat.wiki/release/ypyse6ff4nbzrfd44resyav25m
* [ ] if title and publisher matches, but DOI and year is different, assume
different, e.g. https://fatcat.wiki/release/k3hutukomngptcuwdys5omv2ty,
https://fatcat.wiki/release/xmkiqj4bizcwdaq5hljpglkzqe, or
https://fatcat.wiki/release/phuhxsj425fshp2jxfwlp5xnge and
https://fatcat.wiki/release/2ncazub5tngkjn5ncdk65jyr4u -- these might be repeatedly published
* [ ] article and "reply", https://pubmed.ncbi.nlm.nih.gov/5024865/, https://onlinelibrary.wiley.com/doi/abs/10.5694/j.1326-5377.1972.tb47249.x
* [ ] figshare uses versions, too, https://fatcat.wiki/release/zmivcpjvhba25ldkx27d24oefa, https://fatcat.wiki/release/mjapiqe2nzcy3fs3hriw253dye
* [ ] zenodo has no explicit versions, but ids might be closeby, e.g. https://fatcat.wiki/release/mbnr3nrdijerto6wfjnlsmfhga, https://fatcat.wiki/release/mbnr3nrdijerto6wfjnlsmfhga

#### 100 examples

* accuracy at around 0.8
* while the results look ok, the reasons are not always the ones that stand out
  the most (while checking manually)

```
78 [x]
11 [o]
11 [ ]
```

[ ] https://fatcat.wiki/release/i2ziaqjrovh3rfrojcaf2xqidy https://fatcat.wiki/release/4rbsv4kplnf4tny22px5z35vty Status.DIFFERENT Miss.CONTRIB_INTERSECTION_EMPTY
[o] https://fatcat.wiki/release/65qk35lrxfbqxnpjfpra3ankxe https://fatcat.wiki/release/tovzgangzbfm5bc2qriyh2k6da Status.AMBIGUOUS OK.DUMMY
[x] https://fatcat.wiki/release/foddwpevbjao3b3uwccvtuxfi4 https://fatcat.wiki/release/versjalccvgdtp3q25elgy2z7a Status.DIFFERENT Miss.DATASET_DOI
[x] https://fatcat.wiki/release/v2ypxs2yrbh57cdo6lfuiik64e https://fatcat.wiki/release/6zzx36tlefdtbftzpg4wtump3e Status.STRONG OK.ARXIV_VERSION
[ ] https://fatcat.wiki/release/qvlzvflp6vhojdm3uyvj2d6keq https://fatcat.wiki/release/vynqlyi2xjdexmf54a5yfidx6m Status.DIFFERENT Miss.RELEASE_TYPE
[x] https://fatcat.wiki/release/hdvg6m467bhyng4l7xauk4ymoa https://fatcat.wiki/release/f5fugxp3qze2fht2uxt3xivi4i Status.STRONG OK.PREPRINT_PUBLISHED
[x] https://fatcat.wiki/release/cubz67ifbvacppya3i27yiwr2q https://fatcat.wiki/release/4ojllezvyfehnpnj2pil2h2pdu Status.EXACT OK.TITLE_AUTHOR_MATCH
[o] https://fatcat.wiki/release/hfewgpty4ne3zn7rg32z5npdxy https://fatcat.wiki/release/3djtma4xrjh2pcxy4gu6pafqji Status.AMBIGUOUS OK.DUMMY
[x] https://fatcat.wiki/release/s46mfwvb4rdyhlforb6yxg3abi https://fatcat.wiki/release/5hvdhbszafhw5fbu4jnrmesdmu Status.DIFFERENT Miss.BOOK_CHAPTER
[x] https://fatcat.wiki/release/mn26hwbmqvh23jhsecoder3ixq https://fatcat.wiki/release/544v67u75fazfp5qssqzmh6fta Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/4srjsirjhvhvtenz23lg6bqnqu https://fatcat.wiki/release/3czbwace7bh4hkfehzntnddt2i Status.STRONG OK.ARXIV_VERSION
[ ] https://fatcat.wiki/release/ybxygpeypbaq5pfrztu3z2itw4 https://fatcat.wiki/release/2c2ztrtlkzdhfmzpf7fbindpjq Status.DIFFERENT Miss.DATASET_DOI
[x] https://fatcat.wiki/release/vokr6qxyqrc55kyn45dyavr2lq https://fatcat.wiki/release/b5helm53ljdxjpxdnn5zjqpjve Status.EXACT OK.TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/kgeynply6vcxdeiluu6es6w72m https://fatcat.wiki/release/cm536ige6bfdfhhesp26ibfdva Status.EXACT OK.TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/knwc764q25f33ib6qnwo7pyaui https://fatcat.wiki/release/n74tqiqi5jcx5d6vl5f7lpokaa Status.DIFFERENT Miss.CONTRIB_INTERSECTION_EMPTY
[x] https://fatcat.wiki/release/eo4qptzoqrholjslj7nemlne2y https://fatcat.wiki/release/zisq3tsezjcejinlpf7qgk6z2i Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/crsd5c2fhvd7hodbd4trne3lgi https://fatcat.wiki/release/4547ybo5hvf4xhlh5triaccxai Status.DIFFERENT Miss.RELEASE_TYPE
[o] https://fatcat.wiki/release/eyol2bjf6jawhjnote73ej5v24 https://fatcat.wiki/release/jowohxiuuncqbdidvqjrrb5324 Status.AMBIGUOUS OK.DUMMY
[x] https://fatcat.wiki/release/egxon2iqljf47c4stvacnccvwy https://fatcat.wiki/release/swuxb5owx5g4hff3c7ur5x3awy Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/kob434ccgbhu3ecnwnqzsb6e3a https://fatcat.wiki/release/wbw3dpl44zew3bjcwfvqtk2b2q Status.DIFFERENT Miss.RELEASE_TYPE
[ ] https://fatcat.wiki/release/d5bqydkylzelpmdfcks2v5th7q https://fatcat.wiki/release/lzcgl52npjaf3etfhhnb3d46da Status.DIFFERENT Miss.DATASET_DOI
[o] https://fatcat.wiki/release/5ysvoxjj4jcxbji42nnzapr6n4 https://fatcat.wiki/release/dx6wevs345cjfejokze2te6sia Status.AMBIGUOUS OK.DUMMY
[x] https://fatcat.wiki/release/c2pranaprjhrxk7x5euws32cg4 https://fatcat.wiki/release/liarb7xuizewdafcubg2z3dwou Status.DIFFERENT Miss.RELEASE_TYPE
[x] https://fatcat.wiki/release/tyokc7ccfjaw5nimkkl32dl6ta https://fatcat.wiki/release/gyyxomlfkzfannusvzoypbnel4 Status.AMBIGUOUS Miss.BLACKLISTED
[x] https://fatcat.wiki/release/2wakwcyb2zhbla2aao3g6ajfli https://fatcat.wiki/release/dryvgf7v3jeergr3gendplglqq Status.DIFFERENT Miss.CONTRIB_INTERSECTION_EMPTY
[o] https://fatcat.wiki/release/xdclbyjgjnbehchrl7l2vi3274 https://fatcat.wiki/release/t3kqh6lfprfaff5zovh6qlodxy Status.AMBIGUOUS OK.DUMMY
[x] https://fatcat.wiki/release/zvwqju7e3zhf7jpbtoejfe3i4y https://fatcat.wiki/release/fpj5eqgiunfpjn7qkffwvpre5e Status.DIFFERENT Miss.CONTRIB_INTERSECTION_EMPTY
[x] https://fatcat.wiki/release/cwfhdsdr6nbtngqwsqpafqj72u https://fatcat.wiki/release/icrvubkwprh6fl2irtrxziqqai Status.STRONG OK.ARXIV_VERSION
[x] https://fatcat.wiki/release/qlkjwemcrzcpjeeecduiunghui https://fatcat.wiki/release/chejpgnhebcx7of4d4dkuqhkne Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/no7a4vrfwnfp7jqrliq6n2hpxi https://fatcat.wiki/release/rscsor4cl5fydedr2jb6o7k4zi Status.DIFFERENT Miss.RELEASE_TYPE
[o] https://fatcat.wiki/release/aogvyiw67vdsnf26bufauy2rqa https://fatcat.wiki/release/aofedljjhbhajmx5doxfcv43fa Status.AMBIGUOUS OK.DUMMY
[x] https://fatcat.wiki/release/mxfrtcc3njeh5dscwgzhrugzsq https://fatcat.wiki/release/x7lbkuc5afb75nz5l5kyrzy2ia Status.DIFFERENT Miss.YEAR
[o] https://fatcat.wiki/release/cjal2f6k5zesxcnrnyhc6ftg5e https://fatcat.wiki/release/oi5kzjlku5gpxjc247v6zjzosa Status.AMBIGUOUS OK.DUMMY
[o] https://fatcat.wiki/release/o6e6yf37y5bttbrpo4piska4gq https://fatcat.wiki/release/pchjd5fwqjdqfevphjff7ydeae Status.AMBIGUOUS OK.DUMMY
[x] https://fatcat.wiki/release/cqkm3hyn3rgcng3d3alwtciwpq https://fatcat.wiki/release/unwrwze6znf5xouud35i3jlneq Status.STRONG OK.SLUG_TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/fzs6y277zbgxnbcsmmfnftyqgy https://fatcat.wiki/release/b2ggrb2mpvh4namvf6mht5nnaq Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/qgvu7i5eqrakpcnantqikaxpbu https://fatcat.wiki/release/kafrljfrv5favpvbgxavobh46y Status.AMBIGUOUS Miss.SHORT_TITLE
[x] https://fatcat.wiki/release/qbfao6tzh5gkxaqaqwmidpme3q https://fatcat.wiki/release/whyzodcvtzehjdvj5ezvbkda34 Status.DIFFERENT Miss.SUBTITLE
[x] https://fatcat.wiki/release/ml7eci5bmnc4zl6fc6vzscciwu https://fatcat.wiki/release/rsjv7rxzuzdptmfn7orwxr7n6q Status.STRONG OK.ARXIV_VERSION
[x] https://fatcat.wiki/release/3mup7xynsfdpne3rtp274lmwdy https://fatcat.wiki/release/pbhkek57zrddnllui7pl4vjhai Status.DIFFERENT Miss.CONTRIB_INTERSECTION_EMPTY
[x] https://fatcat.wiki/release/lr5emu7qpfdmve6jcfjlrgoi64 https://fatcat.wiki/release/revp263aa5dnjft72qynhzjcvi Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/bvu4qrzfvfdhxpvl4k2ertxkbe https://fatcat.wiki/release/qnteujy54vflrnjtq2k4wtrabq Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/gzmkqlwx4vd7vdtnlhkd2md2wy https://fatcat.wiki/release/7uu7g6k7grbrzlhhibf4q55odm Status.DIFFERENT Miss.RELEASE_TYPE
[x] https://fatcat.wiki/release/apbr2crzrfamhdqt35c3sgkld4 https://fatcat.wiki/release/fwhmikkv7rcjdp6j6vmroggncy Status.STRONG OK.SLUG_TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/3x5gxfal75geppn22rck3bdanm https://fatcat.wiki/release/fpjygddf7bgahaaabjl2d67m4i Status.EXACT OK.TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/mkqmxbrhozhxphemdgshl57m3u https://fatcat.wiki/release/ahlp3vywzzb5fh5tbjskaym3ri Status.DIFFERENT Miss.CONTRIB_INTERSECTION_EMPTY
[x] https://fatcat.wiki/release/2hquztvjlrai3frazkmb6icgzy https://fatcat.wiki/release/ygkmoig5fjhtbg3rcobuy67pnu Status.AMBIGUOUS Miss.SHORT_TITLE
[x] https://fatcat.wiki/release/uzrpjthgpbb2hhacohndcgj3qm https://fatcat.wiki/release/gxbp2vmubnhgrhfobb7wceujvm Status.STRONG OK.ARXIV_VERSION
[x] https://fatcat.wiki/release/fmeud4dykjfudb5kjr2fgmaneq https://fatcat.wiki/release/iid2bnrjjbegtpgmpuppjou4k4 Status.DIFFERENT Miss.SUBTITLE
[x] https://fatcat.wiki/release/zmivcpjvhba25ldkx27d24oefa https://fatcat.wiki/release/mjapiqe2nzcy3fs3hriw253dye Status.EXACT OK.TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/lynlkp7wh5hn3mlpzcfz4faoqi https://fatcat.wiki/release/yrbvjd4xrjaq3jxt7pkheysclm Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/t3vpox5wrvbgtcigp6a6o64oey https://fatcat.wiki/release/q5yaj5zbzjctzapb5bztzctsoe Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/65qtai5dmjb2hmkwa73nwafyhu https://fatcat.wiki/release/p4lk4tbohjat3g5nn5pb3kjdyu Status.DIFFERENT Miss.RELEASE_TYPE
[x] https://fatcat.wiki/release/fqtc2tonfbh7hlcwoxgxzqi4lu https://fatcat.wiki/release/ng7utp7murge3ksuzbtljf5bsq Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/mbnr3nrdijerto6wfjnlsmfhga https://fatcat.wiki/release/ddikrsxnajblvchthiwcbsmiue Status.EXACT OK.TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/nqfv37as6bcohketfrhiuac2mq https://fatcat.wiki/release/ty6megtz35c3hep57bbx2cetja Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/cedhaxcvkrddpeedqtaxln4zsq https://fatcat.wiki/release/5hzpesjrjrdrzaoahvihorp7eq Status.STRONG OK.PREPRINT_PUBLISHED
[x] https://fatcat.wiki/release/wwiarqhsgbevdc74f6i4qmvyhy https://fatcat.wiki/release/d35gplnuibe6djfhnh42o66zbm Status.DIFFERENT Miss.CONTRIB_INTERSECTION_EMPTY
[x] https://fatcat.wiki/release/arzle77ezbbz5e33ghpqlwjw5e https://fatcat.wiki/release/e6ism7bt2vf5jl4v2ffwy3gqvu Status.DIFFERENT Miss.SUBTITLE
[x] https://fatcat.wiki/release/yv3ihfy6pfe4xblrj7dcf3674u https://fatcat.wiki/release/tmewuet24jg5dflspneju2cot4 Status.STRONG OK.ARXIV_VERSION
[x] https://fatcat.wiki/release/rh3r3fncmzaulfdfrjzv25tpli https://fatcat.wiki/release/7zp3azvi4vbxxob2cdyzm6pepa Status.EXACT OK.TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/lf7w27ma2ncjjpwoy2kl22t77e https://fatcat.wiki/release/mgxkqlohmbhfpedxwg3s5jhrrq Status.DIFFERENT Miss.RELEASE_TYPE
[ ] https://fatcat.wiki/release/l4fyyvsckneuxkq7d3y2zvkvbe https://fatcat.wiki/release/gf5hriyvuvarhcvttnooaffksi Status.DIFFERENT Miss.RELEASE_TYPE
[x] https://fatcat.wiki/release/libbt4mcwng3tiwcutfaxewmjy https://fatcat.wiki/release/6csob32ld5dx7h63cssqly6rfm Status.DIFFERENT Miss.RELEASE_TYPE
[ ] https://fatcat.wiki/release/7nbcgsohrrak5cuyk6dnit6ega https://fatcat.wiki/release/q66xv7drk5fnph7enwwlkyuwqm Status.DIFFERENT Miss.CONTRIB_INTERSECTION_EMPTY
[ ] https://fatcat.wiki/release/2tzvdvx4t5hfxnqlnyt4rqenly https://fatcat.wiki/release/houszjo2ejbjhljxvxz23whgua Status.DIFFERENT Miss.DATASET_DOI
[x] https://fatcat.wiki/release/2r6dem2qanfttn73lezeislize https://fatcat.wiki/release/4iksfoith5b6zjarfihdtosr3e Status.STRONG OK.ARXIV_VERSION
[x] https://fatcat.wiki/release/wif435fwunfpfd46vvxo3at5ya https://fatcat.wiki/release/fy3j2l4s55b7ffltpiaic2jj7i Status.DIFFERENT Miss.YEAR
[ ] https://fatcat.wiki/release/qsxbwvreu5ehrbz65ngh2ghcra https://fatcat.wiki/release/xjvo37ynxvc3zm55bxoa545gvq Status.EXACT OK.TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/huophilkpbh2ddemt7okzzkuyq https://fatcat.wiki/release/crle5axqrfhfdob464wlwhfrf4 Status.AMBIGUOUS Miss.SHORT_TITLE
[x] https://fatcat.wiki/release/dcq2jgd5abbjflzun4n3v6gjh4 https://fatcat.wiki/release/ptovjgczrvft5fq2plyldafniq Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/7ah6efvk2ncjzgywch2cmtfumq https://fatcat.wiki/release/nj7v4e3cxbfybozjmdiuwqo4sm Status.DIFFERENT Miss.RELEASE_TYPE
[x] https://fatcat.wiki/release/eu4xst6zx5atfj37mvwdm54opq https://fatcat.wiki/release/7b7vnb7bc5g5va4yk72ruajok4 Status.EXACT OK.TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/6ovhnujfsff2nhnoeimjcckgta https://fatcat.wiki/release/qeujgsfrmvft7k7r474maekvua Status.DIFFERENT Miss.DATASET_DOI
[ ] https://fatcat.wiki/release/ggzzwt6deneyrna5h65mvv7sfe https://fatcat.wiki/release/h4rnaxua75dndmq4x4snnw3qxe Status.AMBIGUOUS Miss.SHORT_TITLE
[x] https://fatcat.wiki/release/muk4xhjhubc3xn6qqddllgfsly https://fatcat.wiki/release/2gywie7yqfflnl6tljfo36keqi Status.STRONG OK.ARXIV_VERSION
[x] https://fatcat.wiki/release/iywyis7npngxxbco6fgjrclrzy https://fatcat.wiki/release/anhsfjxg3few5nkfsvheehiebq Status.DIFFERENT Miss.BOOK_CHAPTER
[ ] https://fatcat.wiki/release/skxiyp7qmraqhe2o4zvo7iq6sq https://fatcat.wiki/release/qyqre3mzgbha7hhfarn5absqnq Status.EXACT OK.TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/rk7mn5uaqjaslgcxc2nl6ijpaq https://fatcat.wiki/release/td3rnxzbxzeslj6ijoce3mtxcq Status.STRONG OK.ARXIV_VERSION
[x] https://fatcat.wiki/release/ohkfrjjcxfcavoqoqt52wi6eke https://fatcat.wiki/release/egufgu3yubgthex3y7fdt7uupa Status.DIFFERENT Miss.DATASET_DOI
[x] https://fatcat.wiki/release/dklwsz4w3rdlfddif4pcxb6ngm https://fatcat.wiki/release/wsbinmv7lragjnaedbgws6bztm Status.DIFFERENT Miss.RELEASE_TYPE
[x] https://fatcat.wiki/release/jizydliu2vclvpdtcrajlvuq2m https://fatcat.wiki/release/3g6mdd3tvjabdaez6mwcycso3q Status.STRONG OK.SLUG_TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/fvrscdvsznb4zlhuadd6ar7ot4 https://fatcat.wiki/release/57la45yryjd73gav22bnl4lyni Status.EXACT OK.TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/6fedywjyynbxhdqv3etxjuqhba https://fatcat.wiki/release/gls2x7ca4nhzrkf437gdnj6ekq Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/7lepq6lyyfepdjat6ohpeqycdu https://fatcat.wiki/release/cfm6qhhxovferl2fahf6jmcsiu Status.DIFFERENT Miss.YEAR
[o] https://fatcat.wiki/release/am53f7iyyvcjnjsgjbz7pu7dii https://fatcat.wiki/release/kdubht33hfb4dmghm2g27ck24i Status.AMBIGUOUS OK.DUMMY
[x] https://fatcat.wiki/release/ijbm7t2mpjcrrjazrmeli6b42a https://fatcat.wiki/release/7ijg4ar62rgo3olfbxltltrzc4 Status.EXACT OK.TITLE_AUTHOR_MATCH
[x] https://fatcat.wiki/release/hyt2ebpmhjg53f5eu4v5zortfm https://fatcat.wiki/release/ceu2t7fapvg43bvyyqck344pei Status.DIFFERENT Miss.SUBTITLE
[x] https://fatcat.wiki/release/uhih3c4gbzdtnciiqlfjx3w6le https://fatcat.wiki/release/lgga6cjz6bgo7cszpjfhpuoaqi Status.DIFFERENT Miss.RELEASE_TYPE
[x] https://fatcat.wiki/release/53w5pycrmvgglludwsv44m3czu https://fatcat.wiki/release/mvdjwqdvxfh3vd3zotf3gljm4a Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/6vejogvunnbb7etjzu4yfs32mm https://fatcat.wiki/release/g53ggmce2rek5lw2l52oaimgiq Status.DIFFERENT Miss.YEAR
[x] https://fatcat.wiki/release/325je3kjkjeerkchimvz6qxyji https://fatcat.wiki/release/ir7i7ldr7ffuvigvv6cvyyc7ju Status.DIFFERENT Miss.BOOK_CHAPTER
[x] https://fatcat.wiki/release/hqwrsqnzdjbqhbrqnsbooohqse https://fatcat.wiki/release/ydx2wolhvffxnb6as6gekmocx4 Status.STRONG OK.ARXIV_VERSION
[x] https://fatcat.wiki/release/vz7q453kr5ds3ptsldwxedbiii https://fatcat.wiki/release/2wzybzqlmjhjfh75cxjohbvzi4 Status.DIFFERENT Miss.RELEASE_TYPE
[x] https://fatcat.wiki/release/efumvvpw6jbb7ehp2qfdatgxzy https://fatcat.wiki/release/funn7cwjbrgefji27tzpl4avuu Status.STRONG OK.ARXIV_VERSION
[ ] https://fatcat.wiki/release/ofmeeajuovbqbhkgh4rujkd3xu https://fatcat.wiki/release/r6bvy6cglfe5xgafvdcokawkue Status.DIFFERENT Miss.RELEASE_TYPE
[o] https://fatcat.wiki/release/lezvxt2oong6xm3e3cgp47wsla https://fatcat.wiki/release/aad6r5am6vfxpbfwycmyudp2qe Status.AMBIGUOUS OK.DUMMY
[o] https://fatcat.wiki/release/5mzzswgebze2tk4apmbwjahp34 https://fatcat.wiki/release/vl7r3uewvvbo5i2gntocy3y2ey Status.AMBIGUOUS OK.DUMMY
[x] https://fatcat.wiki/release/pjvosq3ulzeb5d6w7zijrbz75y https://fatcat.wiki/release/pxkm2asxjnflzkdi5qnfd5fpt4 Status.DIFFERENT Miss.BOOK_CHAPTER
[x] https://fatcat.wiki/release/ji3qg5sajndt7p54u7wumqsjye https://fatcat.wiki/release/hxau2e34bnhhbeucfdrncgmcby Status.DIFFERENT Miss.RELEASE_TYPE

