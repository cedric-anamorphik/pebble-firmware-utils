#!/usr/bin/env python
# By Pavel Volkovitskiy

import os
import sys
import time
import struct

from libpebble import stm32_crc

MAX_NUM_FILES = 256
BYTES_PER_TABLE_ENTRY = 16

def manifest(manifest_file_path, data_chunk_file, num_files, timestamp):
    with open(manifest_file_path, 'wb') as manifest_file:
        with open(data_chunk_file, 'rb') as data_file:
            crc = stm32_crc.crc32(data_file.read())
            manifest_file.write(struct.pack('<III', int(num_files), crc, int(timestamp)))

def table(table_file, pack_file_list, ):
    with open(table_file, 'wb') as table_file:

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

    table(pbfile+'.table', resources)

    with open(pbfile+'.data', 'wb') as f:
        for res in resources:
            f.write(open(res, 'rb').read())

    manifest(pbfile+'.manifest', pbfile+'.data', len(resources), timestamp)

    with open(pbfile, 'wb') as f:
        for t in ('manifest', 'table', 'data'):
            f.write(open(pbfile+'.'+t, 'rb').read())


if __name__ == '__main__':

    if len(sys.argv) < 3:
        print('Usage: {} src_dir outfile')
        sys.exit(1)

    src_dir = sys.argv[1]
    pbfile = sys.argv[2]

    resources = sorted([ '/'.join((src_dir, f)) for f in os.listdir(src_dir)])

    pack(resources, pbfile)

