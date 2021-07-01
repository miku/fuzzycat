import pytest
import os

from fuzzycat.utils import (author_similarity_score, cut, jaccard, nwise, slugify_string,
                            token_n_grams, tokenize_string, parse_page_string, dict_key_exists,
                            zstdlines, es_compat_hits_total, clean_doi)


def test_slugify_string():
    assert slugify_string("") == ""
    assert slugify_string("X") == "x"
    assert slugify_string("Xx") == "xx"
    assert slugify_string("Xx x") == "xx x"
    assert slugify_string("Xx x  x") == "xx x x"
    assert slugify_string("Xx?x  x") == "xxx x"
    assert slugify_string("Xx? ?x  x") == "xx x x"
    assert slugify_string("Xx?_?x--x") == "xxxx"
    assert slugify_string("=?++*") == ""


def test_cut():
    assert cut()("a	b") == "a"
    assert cut(1)("a	b") == "b"
    assert cut(2, sep=',')("a,b,c") == "c"
    assert cut(3, sep=',')("a,b,c") == ""
    with pytest.raises(ValueError):
        cut(3, sep=',', ignore_missing_column=False)("a,b,c") == ""


def test_author_similarity_score():
    assert author_similarity_score("", "") == 0.0
    assert author_similarity_score("Gregor Samsa", "G. Samsa") == 0.42857142857142855
    assert author_similarity_score("Geronimo Samsa", "G. Samsa") == 0.375


def test_jaccard():
    assert jaccard(set(), set()) == 0
    assert jaccard(set(["a"]), set()) == 0
    assert jaccard(set(["a"]), set(["a"])) == 1.0
    assert jaccard(set(["a", "b"]), set(["a"])) == 0.5
    assert jaccard(set(["a"]), set(["a", "b"])) == 0.5
    assert jaccard(set(["a", "b", "c"]), set(["a", "c"])) == 2 / 3


def test_token_n_grams():
    assert token_n_grams("") == []
    assert token_n_grams("a") == ["a"]
    assert token_n_grams("abc") == ["ab", "c"]
    assert token_n_grams("abc", n=3) == ["abc"]
    assert token_n_grams("abc", n=1) == ["a", "b", "c"]
    assert token_n_grams("abc hello world", n=3) == ["abc", "hel", "lo", "wor", "ld"]


def test_tokenize_string():
    assert tokenize_string("") == []
    assert tokenize_string("a") == ["a"]
    assert tokenize_string("a b") == ["a", "b"]
    assert tokenize_string("a  b  ") == ["a", "b"]
    assert tokenize_string("a b=c") == ["a", "b=c"]
    assert tokenize_string("a b 1999") == ["a", "b", "1999"]
    assert tokenize_string("a?b*1999") == ["a?b*1999"]


def test_nwise():
    assert list(nwise("1234")) == [("1", "2"), ("3", "4")]
    assert list(nwise("1234", n=1)) == [("1", ), ("2", ), ("3", ), ("4", )]
    assert list(nwise([1, 2, 3, 4, 5], n=3)) == [(1, 2, 3), (4, 5)]


def test_dict_key_exists():
    assert dict_key_exists({}, "") is False
    assert dict_key_exists({"a": "a"}, "a") == True
    assert dict_key_exists({"a": "a"}, "b") == False
    assert dict_key_exists({"a": {"b": "c"}}, "a.b") == True
    assert dict_key_exists({"a": {"b": None}}, "a.b") == True
    assert dict_key_exists({"a": {"b": "c"}}, "a.b.c") == False


def test_page_page_string():
    reject = ("", "123-2", "123-120", "123a-124", "-2-1", "I-II", "xv-xvi", "p")
    for s in reject:
        with pytest.raises(ValueError):
            assert parse_page_string(s)
    assert parse_page_string("123") == (123, None, None)
    assert parse_page_string("90-90") == (90, 90, 1)
    assert parse_page_string("123-5") == (123, 125, 3)
    assert parse_page_string("123-125") == (123, 125, 3)
    assert parse_page_string("123-124a") == (123, 124, 2)
    assert parse_page_string("1-1000") == (1, 1000, 1000)
    assert parse_page_string("p55") == (55, None, None)
    assert parse_page_string("p55-65") == (55, 65, 11)
    assert parse_page_string("e1234") == (1234, None, None)
    assert parse_page_string("577-89") == (577, 589, 13)


def test_zstdlines():
    test_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data/zstd")
    examples = (
        (os.path.join(test_dir, "lines.txt.zst"), os.path.join(test_dir, "lines.txt")),
        (os.path.join(test_dir, "empty.txt.zst"), os.path.join(test_dir, "empty.txt")),
        (os.path.join(test_dir, "single.txt.zst"), os.path.join(test_dir, "single.txt")),
    )
    for zfn, fn in examples:
        with open(fn) as f:
            assert [s.strip() for s in f.readlines()] == list(zstdlines(zfn))


def test_es_compat_hits_total():
    cases = (
        ({
            "hits": {
                "total": 6
            }
        }, 6),
        ({
            "hits": {
                "total": {
                    "value": 7,
                    "relation": "eq"
                }
            }
        }, 7),
    )
    for r, expected in cases:
        assert es_compat_hits_total(r) == expected

def test_clean_doi():
    assert clean_doi(None) == None
    assert clean_doi("blah") == None
    assert clean_doi("10.1234/asdf ") == "10.1234/asdf"
    assert clean_doi("10.1037//0002-9432.72.1.50") == "10.1037/0002-9432.72.1.50"
    assert clean_doi("10.1037/0002-9432.72.1.50") == "10.1037/0002-9432.72.1.50"
    assert clean_doi("http://doi.org/10.1234/asdf ") == "10.1234/asdf"
    # GROBID mangled DOI
    assert clean_doi("21924DOI10.1234/asdf ") == "10.1234/asdf"
    assert clean_doi("https://dx.doi.org/10.1234/asdf ") == "10.1234/asdf"
    assert clean_doi("doi:10.1234/asdf ") == "10.1234/asdf"
    assert clean_doi("10.7326/M20-6817") == "10.7326/m20-6817"
