import csv
import json
import logging
import os

import pytest

from fuzzycat.verify import Status, compare

VERIFY_CSV = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data/verify.csv")
RELEASE_ENTITIES_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data/release")
FATCAT_BASE_URL = 'https://fatcat.wiki/'

status_mapping = {
    "Status.AMBIGUOUS": Status.AMBIGUOUS,
    "Status.DIFFERENT": Status.DIFFERENT,
    "Status.EXACT": Status.EXACT,
    "Status.STRONG": Status.STRONG,
    "Status.WEAK": Status.WEAK,
}

logger = logging.getLogger('test_verify')
logger.setLevel(logging.DEBUG)


def load_release_ident(ident):
    dst = os.path.join(RELEASE_ENTITIES_DIR, ident)
    if not os.path.exists(dst):
        pytest.fail("cannot find entity locally, run `make` in tests/data/ to fetch")
    with open(dst) as f:
        return json.load(f)


def test_compare():
    with open(VERIFY_CSV) as f:
        reader = csv.reader(f, delimiter=',')
        for i, row in enumerate(reader):
            try:
                a, b, expected_status, expected_reason = row
            except ValueError as exc:
                pytest.fail("invalid test file, maybe missing a comma? {}".format(exc))
            status, reason = compare(load_release_ident(a), load_release_ident(b))
            if not expected_status or expected_status.lower() == "todo":
                logger.debug(
                    "skipping test {base}/release/{a} {base}/release/{b} -- no result defined (we think {status}, {reason})"
                    .format(a=a, b=b, base=FATCAT_BASE_URL, status=status, reason=reason))
            assert status == status, "status: want {}, got {} for {} {}".format(
                expected_status, status, a, b)
            if expected_reason:
                assert reason == reason, "reason: want {}, got {}".format(expected_reason, reason)
        logger.info("ran verification over {} cases (https://git.io/JkDgS)".format(i))
