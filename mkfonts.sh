#!/bin/bash
if [ -z "$2" ]; then
	cat <<EOF
Usage:
$0 short_ver full_ver

Example:
$0 330 3.3

Short version is used for path: vSVER-HW
Full version is used for output file name: Pebble-HW-FVER-LANG-patch.pbz
Version number is number of column in fonts.txt file.
EOF
	exit 1
fi

sver=$1
fver=$2

function calc_vid() {
	ver=$1
	chk=$2
	# calculate column number:
	# get first line (title), split it (cols->lines), number lines, grep version and get line number
	vid=$(sed q fonts.txt | tr '\t' '\n' | nl | grep ${ver} | sed q | awk '{print $1}')
	if [ -n "$chk" ]; then
		if [ -z "$vid" ]; then
			echo "Couldn't find font resource info for fw $fver!"
			exit 1
		fi
	else
		echo "$vid"
	fi
}
calc_vid ${fver} t # primary
calc_vid ${fver}a t # aplite

HARDWARES=(snowy_dvt snowy_s3 spalding ev2_4 v1_5 v2_0)
HARDPLATF=(basalt basalt chalk aplite aplite aplite) # different platforms use different resource sets
LANGS=(LaCyr LaGrHb LaViTh LaRuHb)
UTILS=../pebble-firmware-utils
PATCHPATH=../patches
PATCHES="StringFixer_290"
PATCHINFO=StringFix

if ! [ $sver == "uploaded" ]; then
for hwid in ${!HARDWARES[*]}; do # enumerate indices
	hw=${HARDWARES[hwid]}
	platf=${HARDPLATF[hwid]}
	fver_vid=$fver
	[[ $platf == aplite ]] && fver_vid=${fver_vid}a
	vid=$(calc_vid ${fver_vid})
	echo "Building for hw $hw, platform $platf, column $vid"
	for lang in ${LANGS[*]}; do
		echo "  Building for lang $lang"
		echo

		OUT=Pebble-${fver}-${hw}-${lang}-${PATCHINFO}.pbz
		if [ -e $OUT ]; then
			echo "Already built, skipping"
			continue
		fi

		DIR=v${sver}-${hw}
		pushd $DIR

		RES=RES_${lang}_${sver}_${platf}.pbpack

		if ! [ -e ../$RES ]; then
			echo "Resource pack $RES not found, building"
			if ! [ -e res ]; then
				../$UTILS/unpackFirmware.py system_resources.pbpack
				mv resres res
			fi
			cat ../fonts.txt | grep 'GOTHIC_' | grep -v 'GOTHIC_09' | grep -v '_E' | awk '{print $1" "$'$vid'}' | while read name id; do
				id=$(printf %03d $id)
				rm res/${id}_*
				cp ../$lang/$name res/${id}_${name}
			done
			../$UTILS/packResources.sh -w ~/.pebble-sdk/SDKs/current/sdk-core/pebble -o ../$RES res/*
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

cp *${fver}* repo/
fi

echo
echo '-=-=-'
echo
for lang in ${LANGS[*]}; do
	echo -n "| ${fver} | ${lang} "
	for hw in ${HARDWARES[*]}; do
		echo -n "| [GH](https://github.com/MarSoft/pebble-firmware-utils/raw/builds/Pebble-${fver}-${hw}-${lang}-${PATCHINFO}.pbz) "
	done
	echo "|"
done
