#!/bin/sh

origfile=${1:-patched.pbz}

# we randomize filename to make sure caching will not interfere
filename=patched-$RANDOM.pbz

# remove old files...
adb shell rm '/sdcard/patched-*.pbz'

# push new one
adb push "$origfile" /sdcard/$filename || exit 1

# and show confirmation dialog
adb shell am start \
	-n com.getpebble.android.basalt/com.getpebble.android.main.activity.MainActivity \
	-a android.intent.action.VIEW \
	-d file:///sdcard/$filename

echo
echo "Now please confirm firmware installation on your phone"
