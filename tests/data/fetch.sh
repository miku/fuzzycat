#!/bin/bash
#
# Fetches release entity mentioned in verify.csv and cache them locally.

set -e -u
set -o pipefail

API="https://api.fatcat.wiki/v0"
CSV="verify.csv"
RELEASE_DIR="release"

for prog in curl jq; do
	command -v $prog >/dev/null 2>&1 || {
		echo >&2 "$prog required"
		exit 1
	}
done

# Just release ATM, but could extend to other types.
mkdir -p "$RELEASE_DIR"

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
