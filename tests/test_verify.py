import csv
import json
import os

from fuzzycat.verify import Status, compare

VERIFY_CSV = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data/verify.csv")
RELEASE_ENTITIES_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data/release")

status_mapping = {
    "Status.AMBIGUOUS": Status.AMBIGUOUS,
    "Status.DIFFERENT": Status.DIFFERENT,
    "Status.EXACT": Status.EXACT,
    "Status.STRONG": Status.STRONG,
    "Status.WEAK": Status.WEAK,
}


def load_release_ident(ident):
    dst = os.path.join(RELEASE_ENTITIES_DIR, ident)
    with open(dst) as f:
        return json.load(f)


def test_compare():
    with open(VERIFY_CSV) as f:
        reader = csv.reader(f, delimiter=',')
        for i, row in enumerate(reader):
            a, b, expected_status, expected_reason = row
            status, reason = compare(load_release_ident(a), load_release_ident(b))
            assert status == status, "status: want {}, got {} for {} {}".format(
                expected_status, status, a, b)
            if expected_reason:
                assert reason == reason, "reason: want {}, got {}".format(expected_reason, reason)
