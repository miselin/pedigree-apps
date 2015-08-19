#!/usr/bin/env python2
from __future__ import print_function

import argparse
import logging
import os
import sys

import environment

from support import build
from support import buildsystem
from support import deps
from support import steps
from support import toolchain


VALID_ARCH_TARGETS = ('amd64',)
LOGGING_FORMAT = ('%(asctime)s %(module)-15s %(funcName)-20s %(levelname)-10s '
                  '%(message)s')


log = logging.getLogger()


def build_all(args, packages, env):
    """Takes an ordered list of packages and builds them one-by-one."""

    me = os.getpid()

    built = set()
    notbuilt_deps = set()
    notbuilt_failed = set()
    for name, package in packages:
        if not set(package.build_requires()).issubset(built):
            log.error('Package "%s" build-depends not met.', name)
            notbuilt_deps.add(name)
            continue

        if args.dryrun:
            log.info('Would build package "%s" (dry run).', name)
            built.add(name)
            continue
        elif args.only and name not in args.only:
            log.info('Not building package "%s" (not in list of packages '
                     'to build).', name)
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
        except SystemExit:
            raise
        except Exception:
            log.exception('Building %s failed.', name)
            notbuilt_failed.add(name)
        else:
            built.add(name)

        # If tarball extraction fails, we'll end up here but a) in a child,
        # and b) in the chroot.
        if os.getpid() != me:
            status = 0
            if name in notbuilt_failed:
                status = 1
            exit(status)

    for package in notbuilt_deps:
        log.warning('package "%s" failed to build because of missing build '
                    'dependencies.', package)
    for package in notbuilt_failed:
        log.error('package "%s" failed to build.', package)


def main(argv):
    parser = argparse.ArgumentParser(description='Build ports for Pedigree.')
    parser.add_argument('--target', type=str, choices=VALID_ARCH_TARGETS,
                        required=True, help='Architecture target for builds')
    parser.add_argument('--dryrun', action='store_true',
                        help='Do a dry run: only print the packages that '
                        'would be built')
    parser.add_argument('--only', type=str, nargs='+', required=False,
                        help='Only build the given packages. Build-depends '
                        'will not be built so if this may not create stable '
                        'or successful builds.')
    parser.add_argument('--logfile', type=str, required=False,
                        help='File to write logs to. stdout will be used if '
                        'this is not provided.')
    parser.add_argument('--logformat', type=str, default=LOGGING_FORMAT,
                        help='Log entry format.')
    parser.add_argument('--debug', action='store_true',
                        help='Whether to enable debug logging.')
    args = parser.parse_args()

    # Set up the root logger.
    kwargs = {}
    if args.logfile:
        kwargs['filename'] = args.logfile
        with open(args.logfile, 'w'):
            pass
    if args.debug:
        kwargs['level'] = logging.DEBUG
    else:
        kwargs['level'] = logging.INFO
    kwargs['format'] = args.logformat
    logging.basicConfig(**kwargs)

    # Load up an environment ready for building.
    env = environment.generate_environment(args.target)
    # Drop privileges ASAP if we got run as root.
    if not os.getuid():
        # Release privileges.
        os.setgroups([])
        os.setgid(int(env['UNPRIVILEGED_GID']))
        os.setuid(int(env['UNPRIVILEGED_UID']))

    # Make sure we have a sane toolchain with a useful chroot spec file.
    toolchain.chroot_spec(env)

    # Set up our local pup config.
    toolchain.prepare_package_manager(env)

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

    # All done with logging.
    logging.shutdown()

    return 0


if __name__ == '__main__':
    exit(main(sys.argv))
