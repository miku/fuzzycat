#!/bin/bash
#
# Fetches release entity mentioned in verify.csv and cache them locally.

set -e -u
set -o pipefail

API="https://api.fatcat.wiki/v0"
CSV="verify.csv"

for ident in $(awk -F, '{print $1"\n"$2}' "$CSV"); do
	if [ -f "$ident" ]; then
        >&2 echo "[cached] $ident"
		continue
	fi
	curl -sL --fail "$API/release/$ident" | jq --sort-keys . >"$ident"
done
