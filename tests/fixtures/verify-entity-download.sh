#!/bin/bash
#
# Fetches release entities references in VERIFY.

set -e -u
set -o pipefail

API="https://api.fatcat.wiki/v0"
CSV="verify.csv"

for ident in $(awk '{print $3"\n"$4}' "$CSV"); do
	if [ -f "$ident" ]; then
		continue
	fi
	curl -sL --fail "$API/release/$ident" | jq --sort-keys . >"$ident"
done
