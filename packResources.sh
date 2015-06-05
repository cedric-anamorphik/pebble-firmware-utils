#!/bin/bash

print_help() {
	echo "This script converts list of files to PBPack."
	echo "It uses pbpack_meta_data.py script from Pebble framework,"
	echo "so you should have framework installed."
	echo "Resource files should be already prepared, or extracted from ready pbpack."
	echo
	echo "Usage:"
	echo "packResources.sh [-f] [-w pathToFramework] [-o system_resources.pbpack] [-t timestamp] res_file [...]"
	echo "use -f to force output file overwriting."
}

framework="/opt/pebble"
outfile="system_resources.pbpack"
timestamp=$(date +%s)
overwrite=0

while getopts "h?fw:o:t:" opt; do
	case "$opt" in
		h|\?)
			print_help
			exit 0
			;;
		f)
			overwrite=1
			;;
		w)
			framework=$OPTARG
			;;
		o)
			outfile=$OPTARG
			;;
		t)
			timestamp=$OPTARG
			;;
	esac
done
shift $((OPTIND-1))
[ "$1" == "--" ] && shift

if [ $# -lt 1 ]; then
	echo "Please provide at least one file to put in bundle!"
	echo
	print_help
	exit 1
fi

if [ -e "$outfile" ]; then
	if [ $overwrite -eq 1 ]; then
		echo "Warning: overwriting output file $outfile"
	else
		echo "Will not overwrite existing output file $outfile!"
		echo "Use -f to force."
		exit 1
	fi
fi

fwfile=$framework/Pebble/common/tools/pbpack_meta_data.py
[ -e "$fwfile" ] || fwfile=$framework/Pebble/tools/pbpack_meta_data.py
if ! [ -e "$fwfile" ]; then
	echo "Framework repacking script not found in $framework!"
	exit 1
fi
fwrun="python2 $fwfile"

$fwrun manifest "$outfile".manifest "$timestamp" "$@" || exit 1
$fwrun table "$outfile".table "$@" || exit 1
$fwrun content "$outfile".content "$@" || exit 1

cat "$outfile".manifest "$outfile".table "$outfile".content > "$outfile"
rm "$outfile".manifest "$outfile".table "$outfile".content > /dev/null
echo "Bundle with $# resources saved to $outfile"
