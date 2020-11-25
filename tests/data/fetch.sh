#!/bin/bash
#
# Fetches release entity mentioned in verify.csv and cache them locally.

set -e -u
set -o pipefail

API="https://api.fatcat.wiki/v0"
CSV="verify.csv"

# Just release ATM, but could extend to other types.
mkdir -p release

for ident in $(awk -F, '{print $1"\n"$2}' "$CSV"); do
	dst="release/$ident"
	if [ -f "$dst" ]; then
		echo >&2 "[cached] $dst"
		continue
	fi
	tempfile=$(mktemp)
	curl -sL --fail "$API/release/$ident" | jq --sort-keys . >"$tempfile" && mv "$tempfile" "$dst"
	echo >&2 "[fetched] $dst"
done
