#!/bin/bash

# Latest channels:
# http://pebblefw.s3.amazonaws.com/pebble/ev2_4/release-v2/latest.json
# http://pebblefw.s3.amazonaws.com/pebble/ev2_4/beta/latest.json

ver=$1
short=$2
channel=${3:-release-v2}
[[ $ver == *beta* ]] && channel=beta
if [ -z "$short" ]; then
	echo "Usage: $0 version shorthand [channel]"
	echo "Example: $0 2.2 v220"
	echo "Example: $0 2.9-beta5 v29b5     # channel will be automatigically set to beta"
	exit 1
fi

for hw in ev2_4 v1_5 v2_0; do
	echo "Downloading version $ver for HW $hw"
	mkdir $hw$short
	cd $hw$short
	outfile="Pebble-$ver-${hw}.pbz"
	[ -e "$outfile" ] && rm "$outfile"
	wget "https://pebblefw.s3.amazonaws.com/pebble/$hw/$channel/pbz/Pebble-$ver-$hw.pbz"
	unzip "$outfile"
	cd ..
done
echo "Done."
