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


VALID_ARCH_TARGETS = ('amd64', 'arm')
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
        if ((not args.nodeps) and
                (not set(package.build_requires()).issubset(built))):
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
            # Don't re-build the image.
            steps.create_chroot(env, False)

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

    if notbuilt_deps or notbuilt_failed:
        return 1
    else:
        return 0


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
    parser.add_argument('--only-depends', type=str, nargs='+', required=False,
                        help='Only build the given packages and their '
                        'dependencies.')
    parser.add_argument('--nodeps', action='store_true',
                        help='Ignore missing build dependencies.')
    parser.add_argument('--logfile', type=str, required=False,
                        help='File to write logs to. stdout will be used if '
                        'this is not provided.')
    parser.add_argument('--logformat', type=str, default=LOGGING_FORMAT,
                        help='Log entry format.')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Whether to enable debug logging.')
    parser.add_argument('--buildimages', action='store_true', default=False,
                        help='Whether to build Docker images, or just run '
                             'them.')
    args = parser.parse_args()

    # Set up the root logger.
    kwargs = {}
    if args.logfile:
        kwargs['filename'] = args.logfile
        with open(args.logfile, 'w'):
            pass
    else:
        # Clone stderr so forked children can have their stderr redirected.
        # This allows us to log stdout/stderr from all subprocesses but still
        # have all logging calls end up going to the true stderr.
        # This is only necessary if we aren't already writing logs to a file.
        stderr_dup = os.dup(sys.stderr.fileno())
        log_stream = os.fdopen(stderr_dup, 'w')
        kwargs['stream'] = log_stream
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

    if not args.dryrun:
        # Make sure we have a sane toolchain with a useful chroot spec file.
        toolchain.chroot_spec(env)

        # Set up our local pup config.
        toolchain.prepare_package_manager(env)

        # Prepare our chroot in which building will happen.
        # Don't let this modify our environment just yet.
        steps.create_chroot(env.copy(), args.buildimages)

        # Prepare the cross-toolchain for building. This includes preparing the
        # correct location for libc/libm, libpedigree, etc
        toolchain.prepare_compiler(env)
    else:
        log.info('not touching filesystem, dry run')

    # Get packages to build.
    packages = buildsystem.load_packages(env)

    # Sort dependencies so the build is performed correctly.
    packages = deps.sort_dependencies(packages)

    # Filter based on only/only-depends.
    if args.only_depends:
        actual_packages = []
        wanted_depends = set()
        for name, package in reversed(packages):
            if name in args.only_depends or name in wanted_depends:
                actual_packages.append((name, package))
                wanted_depends.update(package.build_requires())

        packages = tuple(reversed(actual_packages))

    # Build packages.
    result = build_all(args, packages, env)

    # All done with logging.
    logging.shutdown()

    return result


if __name__ == '__main__':
    exit(main(sys.argv))
