#!/usr/bin/env python

from __future__ import print_function

import sys
import urllib


def main():
    key = sys.argv[1]
    deps_path = sys.argv[2]
    deps_arch = sys.argv[3]

    with open(deps_path, 'r') as f:
        contents = f.read()

    postdata = {
        'arch': deps_arch,
        'blob': contents,
        'key': 'upload',
        'key_value': key,
    }
    postdata = urllib.urlencode(postdata)

    url = 'https://the-pedigree-project.appspot.com/deps-%s.svg' % deps_arch

    response = urllib.urlopen(url, postdata)
    result = response.read()

    print(result)


if __name__ == '__main__':
    main()
