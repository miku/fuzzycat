# coding: utf-8

from typing import List, NamedTuple
import pytest

from fuzzycat.utils import *


def test_extract_issns():
    Case = NamedTuple("Case", [("s", str), ("result", List[str])])
    cases = (
        Case("", []),
        Case("Hello 1234", []),
        Case("Hello 1084-5100 World", ["1084-5100"]),
        Case("Hello 10845100 World", []),
        Case("Hello 1084-5100 1084-5100 World", ["1084-5100", "1084-5100"]),
        Case("2323-573X 2169-1886 Journal", ["2323-573X", "2169-1886"]),
    )
    for c in cases:
        result = extract_issns(c.s)
        assert result == c.result


def test_longest_common_prefix():
    Case = NamedTuple("Case", [("a", str), ("b", str), ("result", str)])
    cases = (
        Case("", "", ""),
        Case("a", "", ""),
        Case("ab", "a", "a"),
        Case("123", "123", "123"),
    )
    for c in cases:
        result = longest_common_prefix(c.a, c.b)
        assert result == c.result


def test_common_prefix_length_ratio():
    Case = NamedTuple("Case", [("a", str), ("b", str), ("result", float)])
    cases = (
        Case("", "", 0.0),
        Case("a", "", 0.0),
        Case("Hello World!", "ello", 0.0),
        Case("ab", "a", 0.5),
        Case("123", "123", 1.0),
        Case("1234", "123", 0.75),
    )
    for c in cases:
        result = common_prefix_length_ratio(c.a, c.b)
        assert result == c.result


def test_hamming_distance():
    Case = NamedTuple("Case", [("a", str), ("b", str), ("result", int)])
    cases = (
        Case("", "", 0),
        Case("a", "a", 0),
        Case("a", "ab", 1),
        Case("abc", "cba", 2),
        Case("1234", "", 4),
    )
    for c in cases:
        result = hamming_distance(c.a, c.b)
        assert result == c.result


def test_is_valid_issn():
    cases = {
        "value_error": ("", "1234", "123456", "111122223333", "XXXXXXXX"),
        "valid": (
            "0710-4081",
            "0011-7625",
            "2268-5901",
            "1809-0710",
            "1533-7561",
            "07104081",
            "00117625",
            "22685901",
            "18090710",
            "15337561",
        ),
        "invalid": (
            "0710-4080",
            "0011-7626",
            "2268-5902",
            "1809-0709",
            "1533-7560",
            "07104080",
            "00117626",
            "22685902",
            "18090709",
            "15337560",
        ),
    }
    for ve in cases["value_error"]:
        with pytest.raises(ValueError):
            is_valid_issn(ve)
    for v in cases["valid"]:
        assert is_valid_issn(v) == True
    for v in cases["invalid"]:
        assert is_valid_issn(v) == False


def test_keys_with_values():
    Case = NamedTuple("Case", [("d", Dict), ("result", List[Any])])
    cases = (
        Case({}, []),
        Case({"a": "v"}, ["a"]),
        Case({"a": "", "b": "v"}, ["b"]),
        Case({"a": None, "b": "v"}, ["b"]),
        Case({"a": [], "b": "v"}, ["b"]),
        Case({"a": 0, "b": "v"}, ["b"]),
    )
    for case in cases:
        result = keys_with_values(case.d)
        assert result == case.result
