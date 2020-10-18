# coding: utf-8
"""
Command line entry point for ad-hoc testing.
"""

import argparse

from fatcat_openapi_client import ReleaseEntity, ReleaseExtIds

from fuzzycat.fatcat.matching import match_release_fuzzy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-R", "--release", help="match release", action="store_true")
    parser.add_argument("-t", "--title", help="title")

    args = parser.parse_args()

    if args.release and args.title:
        re = ReleaseEntity(title=args.title, ext_ids=ReleaseExtIds())
        print(match_release_fuzzy(re, es="https://search.fatcat.wiki"))
