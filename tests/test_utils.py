import pytest

from fuzzycat.utils import author_similarity_score, cut, slugify_string, jaccard, token_n_grams, tokenize_string, nwise


def test_slugify_string():
    assert slugify_string("") == ""
    assert slugify_string("X") == "x"
    assert slugify_string("Xx") == "xx"
    assert slugify_string("Xx x") == "xx x"
    assert slugify_string("Xx x  x") == "xx x  x"
    assert slugify_string("Xx?x  x") == "xxx  x"
    assert slugify_string("Xx? ?x  x") == "xx x  x"
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

