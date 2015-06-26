#!/usr/bin/env python2
# URI = 'http://pebble-static.s3.amazonaws.com/watchfaces/index.html'
URIs = {
    1: 'http://pebblefw.s3.amazonaws.com/pebble/ev2_4/release/latest.json',
    2: 'http://pebblefw.s3.amazonaws.com/pebble/ev2_4/release-v2/latest.json',
    3: 'http://pebblefw.s3.amazonaws.com/pebble/snowy_dvt/release-v3/latest.json',
}

import argparse
from urllib2 import urlopen
import hashlib
import logging, os.path
import json

def parse_args():
    parser = argparse.ArgumentParser('Download latest firmware bundle from Pebble')
    parser.add_argument('version', default=3, nargs='?',
                        choices = URIs,
                        help='Which version group to use.')
    return parser.parse_args()

if __name__ == "__main__":
    log = logging.getLogger()
    logging.basicConfig(format='[%(levelname)-8s] %(message)s')
    log.setLevel(logging.DEBUG)

    args = parse_args()

    log.info("Downloading firmware linked from %s" % URIs[args.version])

    page = urlopen(URIs[args.version]).read()
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
