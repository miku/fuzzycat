import pytest
import collections
import tempfile
from fuzzycat.cluster import release_key_title, release_key_title_normalized, release_key_title_nysiis, sort_by_column, group_by
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

def test_release_key_title_authors_ngram():
    pass

def test_sort_by_column():
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tf:
        tf.write("2 b\n")
        tf.write("2 a\n")
        tf.write("9 d\n")
        tf.write("1 c\n")

    fn = sort_by_column(tf.name, opts='-k 2')
    with open(fn) as f:
        lines = [v.strip() for v in f]
        assert lines == ['2 a', '2 b', '1 c', '9 d']

    fn = sort_by_column(tf.name, opts='-k 1')
    with open(fn) as f:
        lines = [v.strip() for v in f]
        assert lines == ['1 c', '2 a', '2 b', '9 d']

    fn = sort_by_column(tf.name, opts='-k 3')
    with open(fn) as f:
        lines = [v.strip() for v in f]
        assert lines == ['1 c', '2 a', '2 b', '9 d']


def test_group_by():
    Case = collections.namedtuple("Case", "seq keyfunc valuefunc result")
    cases = (
        Case(["0", "1"], lambda v: v, lambda v: v, [{
            'k': '0',
            'v': ['0']
        }, {
            'k': '1',
            'v': ['1']
        }]),
        Case(["a 1", "a 2", "b 3"], lambda v: v.split()[0], lambda v: v.split()[1], [{
            'k': 'a',
            'v': ['1', '2']
        }, {
            'k': 'b',
            'v': ['3']
        }]),
    )

    for case in cases:
        assert case.result == list(group_by(case.seq, case.keyfunc, case.valuefunc))

