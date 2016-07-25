#!/bin/sh
# Usage:
# updatefw.sh [filename.pbz]
# filename defaults to patched.pbz

origfile=${1:-patched.pbz}
ext=${origfile##*.}

# we randomize filename to make sure caching will not interfere
filename=patched-$RANDOM.$ext

# remove old files...
adb shell rm '/sdcard/patched-*.'$ext 

# push new one
if ! adb push "$origfile" /sdcard/$filename; then
	echo "Failed to push file to the phone. Is ADB connected?"
	exit 1
fi

# and show confirmation dialog
adb shell am start \
	-n com.getpebble.android.basalt/com.getpebble.android.main.activity.MainActivity \
	-a android.intent.action.VIEW \
	-d file:///sdcard/$filename

echo
echo "Now please confirm firmware installation on your phone"
