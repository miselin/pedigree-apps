#!/usr/bin/env python2
from __future__ import print_function

import argparse
import collections
import imp
import os
import shutil
import sys
import subprocess
import tarfile
import traceback

import environment

from support import build
from support import buildsystem
from support import deps
from support import steps
from support import toolchain
from support import util


VALID_ARCH_TARGETS = ('amd64',)


def build_all(args, packages, env):
    """Takes an ordered list of packages and builds them one-by-one."""

    me = os.getpid()

    built = set()
    notbuilt_deps = set()
    notbuilt_failed = set()
    for name, package in packages:
        if not set(package.build_requires()).issubset(built):
            print('Package "%s" build-depends not met.' % name, file=sys.stderr)
            notbuilt_deps.add(name)
            continue

        if args.dryrun:
            print('Would build package "%s" (dry run).' % name)
            built.add(name)
            continue
        elif args.only and name not in args.only:
            print('Not building package "%s" (not in list of packages to build).' % name)
            built.add(name)
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
            print('Building %s failed: %s' % (name, e.message), file=sys.stderr)
            traceback.print_exc()
            if os.getpid() != me:
                exit(1)  # Exit with non-zero exit status - we're a forked child.
            notbuilt_failed.add(name)
        else:
            built.add(name)

    for package in notbuilt_deps:
        print('WARNING: package "%s" failed to build because of missing build dependencies.' % package)
    for package in notbuilt_failed:
        print('ERROR: package "%s" failed to build.' % package)


def main(argv):
    # Drop privileges ASAP if we got run as root.
    if not os.getuid():
        # Release privileges.
        os.setgroups([])
        os.setgid(int(env['UNPRIVILEGED_GID']))
        os.setuid(int(env['UNPRIVILEGED_UID']))

    parser = argparse.ArgumentParser(description='Build ports for Pedigree.')
    parser.add_argument('--target', type=str, choices=VALID_ARCH_TARGETS,
        required=True, help='Architecture target for the builds.')
    parser.add_argument('--dryrun', action='store_true',
        help='Do a dry run: only the packages that would be built are printed.')
    parser.add_argument('--only', type=str, nargs='+', required=False,
        help='Only build the given packages. Build-depends will not be built '
            'so if this may not create stable or successful builds.')
    args = parser.parse_args()

    # Load up an environment ready for building.
    env = environment.generate_environment(args.target)

    # Make sure we have a sane toolchain with a useful chroot spec file.
    toolchain.chroot_spec(env)

    # Prepare our chroot in which building will happen.
    # Don't let this modify our environment just yet.
    steps.create_chroot(env.copy())

    # Prepare the cross-toolchain for building. This includes preparing the
    # correct location for libc/libm, libpedigree, etc
    toolchain.prepare_compiler(env)

    # Get packages to build.
    packages = buildsystem.load_packages(env)

    # Sort dependencies so the build is performed correctly.
    packages = deps.sort_dependencies(packages)

    # Build packages.
    build_all(args, packages, env)

    return 0


if __name__ == '__main__':
    exit(main(sys.argv))
