#!/usr/bin/env python2
# URI = 'http://pebble-static.s3.amazonaws.com/watchfaces/index.html'
URIs = {
    '1': 'http://pebblefw.s3.amazonaws.com/pebble/{}/release/latest.json',
    '2': 'http://pebblefw.s3.amazonaws.com/pebble/{}/release-v2/latest.json',
    '3': 'http://pebblefw.s3.amazonaws.com/pebble/{}/release-v3/latest.json',
    '3.7': 'http://pebblefw.s3.amazonaws.com/pebble/{}/release-v3.7/latest.json',
    '3.8': 'http://pebblefw.s3.amazonaws.com/pebble/{}/release-v3.8/latest.json',
}
HWs = {
    '1': [
        'ev2_4',
        'v1_5',
    ],
    '2': [
        'ev2_4',    # V2R2
        'v1_5',     # V3Rx
        'v2_0',     # STEEL
    ],
    '3': [
        'ev2_4',      # V2R2
        'v1_5',       # V3Rx
        'v2_0',       # STEEL
        'snowy_dvt',  # Time
        'snowy_s3',   # Time Steel
        'spalding',   # Round
    ],
}

import argparse
from urllib2 import urlopen
import hashlib
import logging, os.path
import json

if __name__ == "__main__":
    log = logging.getLogger()
    logging.basicConfig(format='[%(levelname)-8s] %(message)s')
    log.setLevel(logging.DEBUG)


    parser = argparse.ArgumentParser(
        description='Download latest firmware bundle from Pebble')
    parser.add_argument('version', default='3.7', nargs='?',
                        choices=sorted(URIs.keys()),
                        help='Which version group to use.')
    parser.add_argument('hardware', nargs='?',
                        help='Hardware version to use (see code or pebbledev.org)')

    args = parser.parse_args()


    curr_hws = HWs[args.version[0]]
    if args.hardware:
        if args.hardware not in curr_hws:
            parser.error('Available hardwares for version %s: %s' % (
                args.version,
                ', '.join(curr_hws),
            ))
    else:
        args.hardware = curr_hws[-1]


    uri = URIs[args.version].format(args.hardware)
    log.info("Downloading firmware linked from %s" % uri)

    page = urlopen(uri).read()
    data = json.loads(page)

    firmware = data['normal']['url']
    version  = data['normal']['friendlyVersion']
    sha      = data['normal']['sha-256']

    log.info("Latest firmware version: %s" % version)
    fwfile = firmware[firmware.rindex("/")+1:]
    if os.path.exists(fwfile):
        log.warn('Did not download "%s" because it would overwrite an existing file' % fwfile)
        exit()
    with open(fwfile, "wb") as f:
        download = urlopen(firmware);
        length = int(download.headers["Content-Length"])
        log.info("Downloading %s -> %s" % (firmware, fwfile))

        downloaded = 0

        while downloaded < length:
            data = download.read(1024*50)
            f.write(data)
            downloaded += len(data)
            log.info("Downloaded %.1f%%" % (downloaded * 100.0 / length))

    f = open(fwfile, "rb")
    filesha = hashlib.sha256()
    filesha.update(f.read())
    if(filesha.hexdigest() != sha):
        log.error('File download errer: SHA-256 hash mismatch. Please retry.')
    else:
        log.info('File download done.')
