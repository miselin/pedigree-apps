#!/usr/bin/env python2

import os
import sys

import environment

from support import steps


def main():
    if os.getuid():
        print >>sys.stderr, 'prepareChroot must be run as root.'
        exit(1)

    # Load up an environment ready for building.
    env = environment.generate_environment('')

    print 'Creating chroot, please wait...'
    steps.create_chroot(env)
    print 'Chroot created!'


if __name__ == '__main__':
    main()
