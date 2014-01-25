#Pebble Firmware Utils#
Some tools used for Pebble firmware, now include:

##downloadFirmware.py##
by https://github.com/southwolf

It will download the latest firmware for Pebble.

##unpackFirmware.py##
usage: "unpackFirmware.py normal.pbz [output_dir]"

It will extrack files and resources from normal.pbz
Using stm32_crc.py from https://github.com/PebbleDev/libpebble.git, thanks!

##repackFirmware.py##
Update checksums and pack firmware package with modified resources or tintin_fw binary

##translate.py##
Tool to translate interface of watch to most languages.
Uses data in .po format, available at https://poeditor.com/projects/view?id=13860

##patcher.py##
Simple variant of assembler made to ease process of patching firmware
to implement missing functionality or change other stuff.

Uses data in custom .pbp format. Samples available in patches/ dir.

##calculateCrc.py##
Calculates CRC sum of given file

