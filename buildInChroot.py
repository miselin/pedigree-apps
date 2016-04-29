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

from buildPackages import VALID_ARCH_TARGETS, LOGGING_FORMAT


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
            steps.create_chroot(env)

            # Drop in support files from Pedigree build.
            toolchain.pedigree_into_chroot(env, env['CHROOT_BASE'])

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

    if notbuilt_deps or notbuilt_failed:
        return 1
    else:
        return 0


def main(argv):
    parser = argparse.ArgumentParser(description='Build a specific port while '
                                                 'in the build chroot.')
    parser.add_argument('--target', type=str, choices=VALID_ARCH_TARGETS,
                        required=True, help='Architecture target for builds')
    parser.add_argument('--package', type=str, required=True,
                        help='Package to build.')
    parser.add_argument('--filename', type=str, required=True,
                        help='Downloaded filename to extract.')
    parser.add_argument('--logfile', type=str, required=False,
                        help='File to write logs to. stdout will be used if '
                        'this is not provided.')
    parser.add_argument('--logformat', type=str, default=LOGGING_FORMAT,
                        help='Log entry format.')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Whether to enable debug logging.')
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

    # Verify we're actually in the chroot.
    if not os.path.exists('/pedigree_apps'):
        # Not in chroot.
        log.fatal('buildInChroot.py must be run in the build chroot')
        return 1

    # Load up an environment ready for building.
    env = environment.generate_environment(args.target)
    env.track()
    env['CHROOT_BASE'] = '/'
    env['APPS_BASE'] = '/pedigree_apps'
    env['PEDIGREE_BASE'] = '/pedigree_src'
    env['PACKMAN_SCRIPT'] = 'pup'  # Installed via pip.
    env['PACKMAN_REPO'] = '/package_repo'
    env.track(tracking=False)
    env = environment.generate_environment(args.target, env=env, recurse=False)

    # Collect the package to run.
    packages = buildsystem.load_packages(env)
    package_id = args.package
    package = packages[args.package]

    # Update for the chroot we're presented with (in particular, $PATH).
    steps.chroot_environment_update(env)

    # Build!
    try:
        os.chdir('/')
        result = build.in_chroot(env, packages, package, package_id,
                                 args.filename)
    except:
        log.exception('failed to build package "%s"', package_id)
        result = 1

    # All done with logging.
    logging.shutdown()

    return result


if __name__ == '__main__':
    exit(main(sys.argv))
