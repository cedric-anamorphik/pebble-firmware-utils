#!/usr/bin/env python
# By Pavel Volkovitskiy

import os
import sys
import time
import struct
from tempfile import TemporaryFile

from libpebble import stm32_crc

MAX_NUM_FILES = 256
BYTES_PER_TABLE_ENTRY = 16

def manifest(manifest_file, data_file, num_files, timestamp):
    data_file.seek(0)  # first rewind it..
    crc = stm32_crc.crc32(data_file.read())
    manifest_file.write(struct.pack('<III', int(num_files), crc, int(timestamp)))

def table(table_file, pack_file_list, ):
    cur_file_id = 1
    next_free_byte = 0

    for filename in pack_file_list:
        with open(filename, 'rb') as data_file:
            content = data_file.read()
            length = len(content)
            table_file.write(struct.pack('<IIII', cur_file_id, next_free_byte, length, stm32_crc.crc32(content)))
            cur_file_id += 1
            next_free_byte += length

    # pad the rest of the file
    for i in range(len(pack_file_list), MAX_NUM_FILES):
        table_file.write(struct.pack('<IIII', 0, 0, 0, 0))

def pack(resources, pbfile):

    timestamp = int(time.time())

    with TemporaryFile('manifest') as tmp_manifest, \
         TemporaryFile('table') as tmp_table, \
         TemporaryFile('data') as tmp_data:

        table(tmp_table, resources)

        for res in resources:
            tmp_data.write(open(res, 'rb').read())

        manifest(tmp_manifest, tmp_data, len(resources), timestamp)

        with open(pbfile, 'wb') as f:
            for t in (tmp_manifest, tmp_table, tmp_data):
                t.seek(0)
                f.write(t.read())


if __name__ == '__main__':

    if len(sys.argv) < 3:
        print('Usage: {} src_dir outfile')
        sys.exit(1)

    src_dir = sys.argv[1]
    pbfile = sys.argv[2]

    resources = sorted([ '/'.join((src_dir, f)) for f in os.listdir(src_dir)])

    pack(resources, pbfile)

