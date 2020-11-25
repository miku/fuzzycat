
import sys
import json
import argparse
from typing import List, Optional
from pydantic import BaseModel
from fuzzycat.cluster import sandcrawler_slugify


class CrudeBiblio(BaseModel):
    title: Optional[str]
    subtitle: Optional[str]
    contrib_raw_names: Optional[List[str]]
    year: Optional[int]
    container_name: Optional[str]
    volume: Optional[str]
    issue: Optional[str]
    pages: Optional[str]
    release_ident: Optional[str]
    release_stage: Optional[str]
    release_type: Optional[str]
    work_ident: Optional[str]


def map_releases(in_file, out_file) -> None:
    """
    Reads JSON lines from input, selects a subset of fields to create a
    CrudeBiblio, generates a "key" (sandcrawler style), writes a line to output
    which key, then tab, then JSON of the record.
    """
    
    for line in in_file:
        if not line.strip():
            continue
        re = json.loads(line)
        if not re.get('title'):
            continue
        raw_names = [c['raw_name'] for c in (re.get('contribs') or []) if 'raw_name' in c]
        biblio = CrudeBiblio(
            title=re.get('title'),
            subtitle=re.get('subtitle'),
            contrib_raw_names=raw_names or None,
            year=re.get('year'),
            container_name=re.get('container', {}).get('name') or re.get('extra', {}).get('container_name'),
            volume=re.get('volume'),
            issue=re.get('issue'),
            pages=re.get('pages'),
            release_ident=re.get('ident'),
            release_stage=re.get('release_stage'),
            release_type=re.get('release_type'),
            work_ident=re.get('work_ident'),
        )
        # NOTE: could have multiple key functions here
        key = sandcrawler_slugify(biblio.title)
        biblio_json = biblio.json(exclude_none=True, sort_keys=True)
        print(f"{key}\t{biblio_json}")

def cluster_batch(batch: List[CrudeBiblio]) -> List[List[CrudeBiblio]]:
    return []

def print_clusters(clusters: List[List[CrudeBiblio]]) -> None:
    for c in clusters:
        print(json.dumps([cb.todict(exclude_none=True) for cb in c], sort_keys=True))

def self_cluster(in_file, out_file) -> None:

    last_key = None
    batch = []
    for line in in_file:
        if not line.strip():
            continue
        key, raw = line.split("\t")[0:2]
        biblio = CrudeBiblio.from_json(raw)
        if key != last_key and batch:
            clusters = cluster_batch(batch)
            print_clusters(cluster_batch(batch))
        batch = []
        last_key = key
        batch.append(biblio)

def merge_cluster(left_file, right_file, out_file) -> None:
    raise NotImplementedError

def main():

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.set_defaults(func=None)
    subparsers = parser.add_subparsers()

    sub = subparsers.add_parser('map-releases', help='map a release to key+JSON line')
    sub.set_defaults(func=map_releases)

    sub = subparsers.add_parser('self-cluster', help='takes sorted key+JSON, returns crude clusters')
    sub.set_defaults(func=self_cluster)

    sub = subparsers.add_parser('merge-cluster', help='takes two sorted key+JSON, returns crude clusters')
    sub.set_defaults(func=merge_cluster)


    args = parser.parse_args()

    if args.func == map_releases:
        map_releases(sys.stdin, sys.stdout)
    elif args.func == self_cluster:
        self_cluster(sys.stdin, sys.stdout)
    elif args.func == self_cluster:
        self_cluster(argv.refs_file, argv.releases_file, sys.stdout)
    else:
        raise NotImplementedError

if __name__=="__main__":
    try:
        main()
    except BrokenPipeError:
        pass
