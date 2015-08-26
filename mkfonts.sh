#!/bin/bash
if [ -z "$3" ]; then
	cat <<EOF
Usage:
$0 short_ver full_ver ver_num

Example:
$0 330 3.3.0 9

Short version is used for path: vSVER-HW
Full version is used for output file name: Pebble-HW-FVER-LANG-patch.pbz
Version number is number of column in fonts.txt file.
EOF
	exit 1
fi

sver=$1
fver=$2
vid=$3

HARDWARES="snowy_dvt snowy_s3"
LANGS="LaCyr LaGrHb LaViTh"
UTILS=../pebble-firmware-utils
PATCHPATH=../patches
PATCHES="StringFixer_290"
PATCHINFO=StringFix

for hw in $HARDWARES; do
	echo "Building for hw $hw"
	for lang in $LANGS; do
		echo "  Building for lang $lang"
		echo

		OUT=Pebble-${hw}-${fver}-${lang}-${PATCHINFO}.pbz
		if [ -e $OUT ]; then
			echo "Already built, skipping"
			continue
		fi

		DIR=v${sver}-${hw}
		pushd $DIR

		RES=RES_${lang}_${sver}.pbpack

		if ! [ -e ../$RES ]; then
			echo "Resource pack $RES not found, building"
			if ! [ -e res ]; then
				../$UTILS/unpackFirmware.py system_resources.pbpack
				mv resres res
			fi
			cat ../fonts.txt | grep 'GOTHIC_' | grep -v 'GOTHIC_09' | awk '{print $1" "$'$vid'}' | while read name id; do
				id=$(printf %03d $id)
				rm res/${id}_*
				cp ../$lang/$name res/${id}_${name}
			done
			../$UTILS/packResources.sh -o ../$RES res/*
		fi


		# patch if necessary
		if ! [ -e patched.bin ]; then
			patchlist=$(echo $PATCHES | while read p; do echo "../$PATCHPATH/${p}.pbp"; done)
			../$UTILS/patcher.py --always-append $patchlist --output patched.bin
		fi

		# now build fw
		../$UTILS/repackFirmware.py --tintin-fw patched.bin --respack ../$RES --replace-all ../$OUT

		popd

		echo
	done
	echo
done

megaput *${fver}*
exp=$(megals -e | grep *${fver}*)
variants=""

echo
echo '-=-=-'
echo
cat <<EOF
<h1>Builds for $fver ready</h1>
StringFix patch included. Changelog is <a href="http://developer.getpebble.com/sdk/changelogs/$fver/">here</a>.
<br/><br/>
EOF
for hw in $HARDWARES; do
	echo "<h2>$hw</h2>"
	for lang in $LANGS; do
		OUT=Pebble-${hw}-${fver}-${lang}-${PATCHINFO}.pbz
		mega=$(echo "$exp" | grep $OUT | sed 's/ .*//')
		echo "${lang}: <a href=\"${mega}\">MEGA</a>, Yandex<br/>"
	done
done
