#!/bin/bash
# You need to have Pebble SDK 3.x installed for resource repacking.

fw29="$1"
fw30="$2"
fwout="$3"

if [ -z "fw29" ]; then
	echo "Usage: $0 fw29 fw30 fwOut"
	echo "fw29 is localized version of 2.9.1 firmware from PebbleBits,"
	echo "fw30 is stock or any other 3.0 firmware,"
	echo "and fwOut is desired name of output file."
	exit 1
fi

wd2=$(mktemp -d)
wd3=$(mktemp -d)
sp=$(dirname "$0")
if [ ${sp:0:1} != "/" ]; then
	# if was relative path, convert to absolute
	sp=$(pwd)/"$sp"
fi

# unpack 2.9 fw
"$sp"/unpackFirmware.py "$fw29" "$wd2/"
# unpack 3.0 fw
"$sp"/unpackFirmware.py "$fw30" "$wd3/"

# replace resources in 3.0
while read name id2 id3; do
	rm "$wd3"/res/0"$id3"*
	cp "$wd2"/res/0"$id2"* "$wd3"/res/0"$id3"_"$name"
done <<end
GOTHIC_14	56 70
GOTHIC_14_B	57 71
GOTHIC_18	58 72
GOTHIC_18_B	59 21
GOTHIC_24	60 22
GOTHIC_24_B	61 73
GOTHIC_28	62 74
GOTHIC_28_B	63 75
end
# rebuild resource pack
"$sp"/packResources.sh -o "$wd3"/updated.pbpack "$wd3"/res/*

# build v3 firmware
pushd "$wd3"
"$sp"/repackFirmware.py --replace-all -r updated.pbpack out.pbz
popd
# copy it to place
cp "$wd3"/out.pbz "$fwout"

# clean temp dirs
rm -rf "$wd2" "$wd3"
