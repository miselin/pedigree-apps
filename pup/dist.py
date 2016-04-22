#!/usr/bin/env python

from __future__ import print_function

import base64
import sys
import urllib


def main():
    key = sys.argv[1]
    wheel_path = sys.argv[2]
    version = sys.argv[3]

    with open(wheel_path, 'rb') as f:
        contents = f.read()

    postdata = {
        'version': version,
        'blob': base64.b64encode(contents),
        'key': 'upload',
        'key_value': key,
    }
    postdata = urllib.urlencode(postdata)

    url = 'https://the-pedigree-project.appspot.com/pup.whl'

    response = urllib.urlopen(url, postdata)
    result = response.read()

    print(result)


if __name__ == '__main__':
    main()
