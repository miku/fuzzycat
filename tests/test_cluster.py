import pytest
import collections
import tempfile
from fuzzycat.cluster import release_key_title, release_key_title_normalized, release_key_title_nysiis
import os

Case = collections.namedtuple("Case", 'input output')


def test_release_key_title():
    with pytest.raises(KeyError):
        release_key_title({})
    with pytest.raises(KeyError, match='title'):
        release_key_title({'ident': '123'})
    with pytest.raises(KeyError, match='ident'):
        release_key_title({'title': 'deep learning backdoor'})
    with pytest.raises(ValueError, match='title.*missing'):
        release_key_title({'ident': '', 'title': ''})
    cases = (
        Case(input={
            'ident': '',
            'title': 'simhash'
        }, output=('', 'simhash')),
        Case(input={
            'ident': '',
            'title': 'Simhash'
        }, output=('', 'Simhash')),
        Case(input={
            'ident': '',
            'title': 'Sim  hash'
        }, output=('', 'Sim  hash')),
    )
    for case in cases:
        assert case.output == release_key_title(case.input)


def test_release_key_title_normalized():
    cases = (
        Case(input={
            'ident': '',
            'title': 'simhash'
        }, output=('', 'simhash')),
        Case(input={
            'ident': '',
            'title': 'Simhash'
        }, output=('', 'simhash')),
        Case(input={
            'ident': '',
            'title': 'Sim  hash'
        }, output=('', 'simhash')),
        Case(input={
            'ident': '',
            'title': 'THE year 1929'
        }, output=('', 'theyear1929')),
        Case(input={
            'ident': '',
            'title': '2019?'
        }, output=('', '2019')),
        Case(input={
            'ident': '123',
            'title': 'H~~2019?'
        }, output=('123', 'h2019')),
    )
    for case in cases:
        assert case.output == release_key_title_normalized(case.input), 'failed case {}'.format(
            case.input)


def test_release_key_title_nysiis():
    cases = (
        Case(input={
            'ident': '',
            'title': 'simhash'
        }, output=('', 'SANAS')),
        Case(input={
            'ident': '',
            'title': 'Simhash'
        }, output=('', 'SANAS')),
        Case(input={
            'ident': '',
            'title': 'Sim  hash'
        }, output=('', 'SANAS')),
        Case(input={
            'ident': '',
            'title': 'THE year 1929'
        }, output=('', 'TAR')),
        Case(input={
            'ident': '',
            'title': '2019?'
        }, output=('', '')),
        Case(input={
            'ident': '123',
            'title': 'H~~2019?'
        }, output=('123', 'H')),
        Case(input={
            'ident': '123',
            'title': '世界'
        }, output=('123', '')),
    )
    for case in cases:
        assert case.output == release_key_title_nysiis(case.input), 'failed case {}'.format(
            case.input)
