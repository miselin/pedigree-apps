#!/usr/bin/env python2

import collections
import imp
import os
import shutil
import sys
import subprocess
import tarfile

import environment

from support import build
from support import buildsystem
from support import deps
from support import steps
from support import toolchain
from support import util


VALID_ARCH_TARGETS = ('amd64',)


def build_all(packages, env):
    """Takes an ordered list of packages and builds them one-by-one."""

    built = set()
    for name, package in packages:
        if not set(package.build_requires()).issubset(built):
            print >>sys.stderr, 'Package "%s" build-depends not met.' % name
            continue

        try:
            env = env.copy()

            # Prepare chroot for building this package.
            steps.create_chroot(env)

            # Install our build_requires packages to the chroot path.
            deps.install_dependent_packages(dict(packages), package, env)

            # Build!
            build.build_package(package, env)
        except Exception as e:
            print >>sys.stderr, 'Building %s failed: %s' % (name, e.message)
            raise
        else:
            built.add(name)


def main(argv):
    if len(argv) < 2:
        print >>sys.stderr, 'Usage: buildPackages <arch_target>'
        return 1

    # TODO(miselin): use optparse or argparse or something like that
    if argv[1] not in VALID_ARCH_TARGETS:
        print >>sys.stderr, ('Valid arch_target values: %s' %
            ','.join(VALID_ARCH_TARGETS))
        return 1

    # Load up an environment ready for building.
    env = environment.generate_environment(argv[1])

    # Prepare our chroot in which building will happen (requires elevation).
    # Don't let this modify our environment just yet.
    steps.create_chroot(env.copy())

    # Release privileges.
    os.setgroups([])
    os.setgid(int(env['UNPRIVILEGED_GID']))
    os.setuid(int(env['UNPRIVILEGED_UID']))

    # Prepare the cross-toolchain for building. This includes preparing the
    # correct location for libc/libm, libpedigree, etc
    toolchain.prepare_compiler(env)

    # Get packages to build.
    packages = buildsystem.load_packages(env)

    # Sort dependencies so the build is performed correctly.
    packages = deps.sort_dependencies(packages)

    # Build packages.
    build_all(packages, env)

    return 0


if __name__ == '__main__':
    exit(main(sys.argv))
