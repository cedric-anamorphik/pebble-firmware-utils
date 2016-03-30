#!/bin/bash

# Latest channels:
# http://pebblefw.s3.amazonaws.com/pebble/ev2_4/release-v2/latest.json
# http://pebblefw.s3.amazonaws.com/pebble/ev2_4/beta/latest.json

ver=$1
short=$2
if [[ "$ver" =~ .*/.* ]]; then
	ver_s=${ver%/*}
	ver=${ver#*/}
elif [[ "$ver" =~ 3\.[7891].* ]]; then
	ver_s=${ver_s:-3.8}
else
	ver_s=${ver_s:-$(echo ${ver:-0.0} | sed 's/\..*//')}
fi
channel=${4:-release-v${ver_s}}
[[ $ver == *beta* ]] && channel=beta
if [ -z "$short" ]; then
	echo "Usage: $0 [channel/]version shorthand ['hw_versions' [platform]"
	echo "Example: $0 2.2 v220"
	echo "Example: $0 2.9-beta5 v29b5"
	echo "Example: $0 3/3.6 v360"
	echo "Example: $0 3.8/3.10.1 v3A1"
	exit 1
fi

#hardwares=${3:-ev2_4 v1_5 v2_0}
hardwares=${3:-snowy_dvt snowy_s3 spalding ev2_4 v1_5 v2_0}

for hw in $hardwares; do
	echo "Downloading version $ver for HW $hw"
	mkdir $short-$hw
	cd $short-$hw
	outfile="Pebble-$ver-${hw}.pbz"
	[ -e "$outfile" ] && rm "$outfile"
	wget "https://pebblefw.s3.amazonaws.com/pebble/$hw/$channel/pbz/Pebble-$ver-$hw.pbz" || exit 1
	unzip "$outfile"
	cd ..
done
echo "Done."
