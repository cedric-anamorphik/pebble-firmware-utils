#!/usr/bin/env python2

import zipfile
import os
import io
import json
from libpebble.stm32_crc import crc32
from struct import unpack
import argparse


def mkdir(path):
    try:
        os.mkdir(path)
    except OSError:
        pass

def extract_content(pbz, content, output_dir):
    print('Extracting %s...' % content['name'])
    pbz.extract(content['name'], output_dir)
    data = io.FileIO(output_dir + content['name']).readall()
    crc = crc32(data)
    if crc == content['crc']:
        print('\t[  OK] Checking CRC...')
    else:
        print('\t[Fail] Checking CRC...')
        print("\tIt's %d, but should be %d" % (content['crc'], crc))

def extract_resources(pbpack, resourceMap, output_dir):
    numbers = unpack('I', pbpack.read(4))[0]
    print('Resource pack has %d resources.' % numbers)

    pbpack.seek(4)
    crc_from_json = unpack('I', pbpack.read(4))[0]
    print('Resource pack claims to have crc 0x%X.' % crc_from_json)

    tbl_start = None  # this will be set depending on firmware version
    res_start = None

    offsets = [
        (0x200C, '3.x', 0x0C),
        (0x100C, '2.x', 0x0C),
        (0x101C, '1.x', 0x0C),
    ]
    for ofs, ver, tab in offsets:
        print('Checking CRC with offset {} ({})...'.format(hex(ofs), ver))
        pbpack.seek(ofs)
        crc_resource = crc32(pbpack.read())
        if crc_resource == crc_from_json:
            print('\t[  OK] This looks like {} firmware'.format(ver))
            tbl_start = tab
            res_start = ofs
            break
        else:
            print('\t[????] CRC mismatch: found 0x%X' % crc_resource)
    else:
        print('\t[Fail] CRC check failed!')
        print('\tShould be 0x%X' % crc_from_json)
        print('Resource pack is either malformed or has unknown format.')
        return

    print('Reading resurce headers...')
    resources = {}
    for i in range(numbers):
        pbpack.seek(tbl_start + i * 16)
        index = unpack('i', pbpack.read(4))[0] - 1
        resources[index] = {
            'offset': unpack('i', pbpack.read(4))[0],
            'size': unpack('i', pbpack.read(4))[0],
            'crc': unpack('I', pbpack.read(4))[0]
        }

    for i in range(len(resources)):
        entry = resources[i]
        hasRM = resourceMap and i < len(resourceMap)
        path = resourceMap[i]['file'] if hasRM else 'res/%03d_%08X' % (
            i+1, entry['crc'])
        dirname = os.path.dirname(path)
        filepath = ("/".join((dirname, resourceMap[i]['defName']))
                    if hasRM else path)

        print('Extracting %s...' % filepath)
        mkdir(output_dir + dirname)

        pbpack.seek(res_start + entry['offset'])
        file = open(output_dir + filepath, 'wb')
        file.write(pbpack.read(entry['size']))
        file.close()

        data = io.FileIO(output_dir + filepath).readall()
        crc = crc32(data)
        if crc == entry['crc']:
            print('\t[  OK] Checking CRC...')
        else:
            print('\t[Fail] Checking CRC...')
            print("\tIt's 0x%x, but should be 0x%x" % (crc, entry['crc']))
    print('All resources unpacked.')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ignore-filenames', dest='useNaming',
                        action='store_false', default=True,
                        help='Ignore resource filenames from manifest. '
                        'By default, if manifest contains resource names'
                        '(as in 1.x firmwares), we will name resources'
                        'according to them.'
                        'With this option, resource names will be res/ID_CRC'
                        'where ID is sequence index of resource and CRC is'
                        'its CRC checksum (for comparing)'
                        'On 2.x firmwares, which don\'t contain resource names,'
                        'we always use that scheme.')
    parser.add_argument('infile')
    parser.add_argument('output_dir', nargs='?', default='pebble-firmware/')
    return parser.parse_args()

def main():
    args = parse_args()

    if not args.infile.endswith('pbz'):  # just unpack resources
        extract_resources(open(args.infile, 'rb'), None, 'res')
        return

    if not args.output_dir.endswith('/'):
        args.output_dir += '/'

    print('Will unpack firmware from %s to directory %s, '
          'using %s for filenames' % (
              args.infile, args.output_dir,
              'resource names (if possible)'
              if args.useNaming else 'resource indices'))

    pbz = zipfile.ZipFile(args.infile)

    print('Extracting manifest.json...')
    pbz.extract('manifest.json', args.output_dir)
    manifest = json.load(open(args.output_dir + 'manifest.json', 'rb'))

    firmware = manifest['firmware']
    extract_content(pbz, firmware, args.output_dir)

    if 'resources' in manifest:
        resources = manifest['resources']
        extract_content(pbz, resources, args.output_dir)

        if 'resourceMap' in manifest['debug']:
            resourceMap = manifest['debug']['resourceMap']['media']
            print('Found resource map in manifest. Looks like 1.x firmware.')
            if args.useNaming:
                print('Will use it to name resources correctly. '
                      'To ignore, pass -i option.')
            else:
                print('Will not use it however because of -i option')
        else:
            resourceMap = None
            print("Couldn't find resource map in manifest. "
                  "Looks like 2.x firmware.")
            print('Resources will be named by their indices.')
            args.useNaming = False
        pbpack = open(args.output_dir + resources['name'], 'rb')
        extract_resources(pbpack,
                          resourceMap if args.useNaming else None,
                          args.output_dir)

if __name__ == '__main__':
    main()
