import collections
import csv

Case =  collections.namedtuple("Case", "a b status reason")

def test_verify_cases():
    with open("fixtures/verify.csv") as f:
        reader = csv.reader(f, delimiter=',')
        for row in reader:
            case = Case(row)
            print(case)

