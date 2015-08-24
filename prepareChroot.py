#!/usr/bin/env python2
from __future__ import print_function

import os
import sys

import environment

from support import steps


def main():
    if os.getuid():
        print('prepareChroot must be run as root.', file=sys.stderr)
        exit(1)

    # Load up an environment ready for building.
    env = environment.generate_environment(sys.argv[1])

    print('Creating chroot, please wait...')
    steps.create_chroot(env)
    print('Chroot created!')


if __name__ == '__main__':
    main()
