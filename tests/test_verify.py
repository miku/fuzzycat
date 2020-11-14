import operator
import os
import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from fuzzycat.verify import compare, Status


def test_verify_cases():
    """
    Test verification cases, via yaml.
    """
    status_map = {
        "AMBIGUOUS": Status.AMBIGUOUS,
        "DIFFERENT": Status.DIFFERENT,
        "EXACT": Status.EXACT,
        "STRONG": Status.STRONG,
        "WEAK": Status.WEAK,
    }
    fields = operator.itemgetter("a", "b", "status", "about")
    folder = os.path.join(os.path.dirname(__file__), "test_verify")
    for root, _, files in os.walk(folder):
        for fn in files:
            with open(os.path.join(root, fn)) as f:
                doc = yaml.load(f, Loader=Loader)
                a, b, status, about = fields(doc)
                result, _ = compare(a, b)
                assert status_map.get(status) == result, about
