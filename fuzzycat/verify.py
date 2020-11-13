"""
Verification part of matching.

We represent clusters as json lines. One example input line:

    {
      "v": [
        {...}, ...
      ],
      "k": "1 Grundlagen",
    }

Examples from clustering stage (from a sample of 100k records):

    ["Global residue formula for logarithmic indices of foliations",2]
    ["Glossary",8]
    ["Gordonia sp.",4]
    ["ERRATA",6]
    ["ERRATUM",4]
    ["Editor's Note",8]
    ["Editorial",95]
    ["Editorial Board",154]
    ["Editorial Board & Publication Information",2]
    ...

"""

import collections
import itertools
import json
import operator

get_key_values = operator.itemgetter("k", "v")

# There titles appear too often, so ignore them for now.
TITLE_BLACKLIST = set([
    "",
    "abstracts",
    "acknowledgements",
    "acknowledgments",
    "announcement",
    "announcements",
    "arthrobacter sp.",
    "author index",
    "back matter",
    "backmatter",
    "bibliography",
    "book review",
    "book reviews",
    "books received",
    "calendar",
    "conclusion",
    "conclusions",
    "contents",
    "contributors",
    "copyright",
    "correction",
    "correspondence",
    "corrigendum",
    "cover",
    "dedication",
    "discussion",
    "editorial",
    "editorial board",
    "einleitung",
    "erratum",
    "foreword",
    "front cover",
    "front matter",
    "frontmatter",
    "gbif occurrence download",
    "index",
    "inhalt",
    "in this issue",
    "introduction",
    "issue information",
    "letters to the editor",
    "letter to the editor",
    "masthead",
    "miscellany",
    "news",
    "not available",
    "notes",
    "occurrence download",
    "[others]",
    "oup accepted manuscript",
    "petitions.xlsx",
    "preface",
    "preliminary material",
    "preservation image",
    "references",
    "reply",
    "reviews",
    "reviews of books",
    "short notices",
    "[s.n.]",
    "streptomyces sp.",
    "subject index",
    "table of contents",
    "taxonomic abstract for the species.",
    "the applause data release 2",
    ":{unav)",
    "奥付",
    "投稿規定",
    "目次",
    "表紙",
    "裏表紙",
])


class GroupVerifier:
    """
    Verifier.

    Within a group, we could have multiple sub clusters, e.g.

    > [AABAB]

    We would need to compare each possible pair and decide whether they are the
    same.
    """
    def __init__(self, iterable: collections.abc.Iterable, max_cluster_size: int = 10):
        self.iterable: collections.abc.Iterable = iterable
        self.max_cluster_size: int = 10
        self.counter = collections.Counter({
            "unique": 0,
            "too_large": 0,
        })

    def run(self):
        for i, line in enumerate(self.iterable):
            if i % 20000 == 0:
                print(i)
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            k, vs = get_key_values(doc)
            if len(vs) < 2:
                self.counter["unique"] += 1
                continue
            if len(vs) > self.max_cluster_size:
                self.counter["too_large"] += 1
                continue
            for a, b in itertools.combinations(vs, r=2):
                result = self.compare(a, b)
                # print(a.get("ident"), b.get("ident"), result)
                # print(a.get("title")[:30], " ---- ", b.get("title")[:20])

        print(json.dumps(dict(self.counter)))

    def compare(self, a, b):
        """
        We compare two release entities here.

        * ext_ids.doi
        * contribs
        * is the title meaningful enough, is it too common, too short
        * files share a sha1
        * arxiv versions
        """
        if len(a.get("title")) < 5:
            self.counter["short_title"] += 1
            return False
        if a.get("title", "").lower() in TITLE_BLACKLIST:
            self.counter["blacklist"] += 1
            return False

        arxiv_id_a = a.get("ext_ids", {}).get("arxiv")
        arxiv_id_b = b.get("ext_ids", {}).get("arxiv")
        if arxiv_id_a and arxiv_id_b:
            id_a, version_a = arxiv_id_a.split("v")
            id_b, version_b = arxiv_id_b.split("v")
            if id_a == id_b:
                self.counter["arxiv_v"] += 1
                return True
            else:
                return False

        a_authors = set([v.get("raw_name") for v in a.get("contribs", [])])
        b_authors = set([v.get("raw_name") for v in b.get("contribs", [])])

        if len(a_authors & b_authors) == 0:
            self.counter["contrib_miss"] += 1
            return False

        self.counter["dummy"] += 1
        return True
