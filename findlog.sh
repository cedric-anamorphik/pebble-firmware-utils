#!/bin/sh
if [ -z $1 ]; then
	echo "Usage: $0 hex_hash"
	exit 1
fi
# get last 4 characters
wcalc 0x${1: -4} | sed 's/^[^0-9]*/\\"/;s/\..*/\\" loghash_dict.json/' | xargs grep
