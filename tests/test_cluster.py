import json
import io
import collections
import os
import tempfile

import pytest

from fuzzycat.cluster import (release_key_title, release_key_title_normalized,
                              release_key_title_nysiis, Cluster)

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


def test_cluster():
    sio = io.StringIO()
    cluster = Cluster([
        json.dumps(line) for line in [
            {
                "title": "hello world",
                "ident": 1
            },
            {
                "title": "hello world!",
                "ident": 2
            },
        ]
    ],
                      release_key_title_normalized,
                      output=sio)
    stats = cluster.run()
    assert stats == {
        "key_fail": 0,
        "key_ok": 2,
        "key_empty": 0,
        "key_denylist": 0,
        "num_clusters": 1
    }
    assert json.loads(sio.getvalue()) == {
        "k": "helloworld",
        "v": [{
            "title": "hello world!",
            "ident": 2
        }, {
            "title": "hello world",
            "ident": 1
        }]
    }

    sio = io.StringIO()
    cluster = Cluster([
        json.dumps(line) for line in [
            {
                "title": "hello world",
                "ident": 1
            },
            {
                "title": "hello world!",
                "ident": 2
            },
            {
                "title": "other",
                "ident": 3
            },
        ]
    ],
                      release_key_title_normalized,
                      output=sio)
    stats = cluster.run()
    assert stats == {
        "key_fail": 0,
        "key_ok": 3,
        "key_empty": 0,
        "key_denylist": 0,
        "num_clusters": 2
    }
    assert [json.loads(line) for line in sio.getvalue().split("\n") if line] == [{
        "k":
        "helloworld",
        "v": [{
            "title": "hello world!",
            "ident": 2
        }, {
            "title": "hello world",
            "ident": 1
        }]
    }, {
        'k':
        'other',
        'v': [{
            'ident': 3,
            'title': 'other'
        }]
    }]
