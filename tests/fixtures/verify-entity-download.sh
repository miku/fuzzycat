#!/bin/bash
#
# Fetches release entity mentioned in verify.csv and cache them locally.

set -e -u
set -o pipefail

API="https://api.fatcat.wiki/v0"
CSV="verify.csv"

for ident in $(awk -F, '{print $1"\n"$2}' "$CSV"); do
	if [ -f "$ident" ]; then
		echo >&2 "[cached] $ident"
		continue
	fi
	tempfile=$(mktemp)
	curl -sL --fail "$API/release/$ident" | jq --sort-keys . >"$tempfile" && mv "$tempfile" "$ident"
	echo >&2 "[fetched] $ident"
done
