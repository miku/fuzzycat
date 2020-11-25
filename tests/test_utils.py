import pytest
from fuzzycat.utils import slugify_string, cut


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
