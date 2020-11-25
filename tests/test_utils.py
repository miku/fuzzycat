import pytest
from fuzzycat.utils import slugify_string, cut, author_similarity_score


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
