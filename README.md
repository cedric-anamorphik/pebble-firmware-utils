#Pebble Firmware Utils#
Some tools used for Pebble firmware.
All tools written by me are licensed by GPL2,
others are property by their corresponding developers.
Now include:

##downloadFirmware.py##
by SouthWolf@github

It will download the latest firmware for Pebble.

##unpackFirmware.py##
original version by xndcn@github and SouthWolf@github,
improved by MarSoft@github
usage: "unpackFirmware.py normal.pbz [output_dir]"

It will extrack files and resources from normal.pbz
Using stm32_crc.py from https://github.com/PebbleDev/libpebble.git, thanks!

##repackFirmware.py##
Update checksums and pack firmware package with modified resources or tintin_fw binary

##calculateCrc.py##
Calculates CRC sum of given file

##translate.py##
Tool to translate interface of watch to most languages.
Uses data in .po format, available at https://poeditor.com/projects/view?id=13860

##patcher.py##
Simple variant of assembler made to ease process of patching firmware
to implement missing functionality or change other stuff.
This program applies patches writen in assembler-like language
to tintin_fw.bin file from firmware

Uses data in custom .pbp format.
Particular patches are available at http://github.com/MarSoft/pebble_firmware_patches.

##findrefs.py##
A tool which takes hexadecimal address,
which is a memory address of string or function
(for functions you should use odd number, i.e. actual address + 1).
It will find all (or most of) references to that address
in given tintin binary.
It supports direct references (aligned by 4), BL and B.W references (aligned by 2).

##lib2idc.py##
This tool takes out relocation table for API functions
from libpebble.a from SDK
and converts it to IDA's IDC format.
Note that resulting file must be further tweaked
for your firmware.

##showimg.py##
Displays b&w image from either tintin binary (by offset)
or from resource file
using '#' for white and ' ' for black.

##prepareResourceProject.py##
Obsolete and currently unsupported project.
It prepares a Pebble app project
to use for repacking resource bundle (pbpack).

