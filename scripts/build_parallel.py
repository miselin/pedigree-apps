#!/usr/bin/env python
# -*- python -*-

from __future__ import print_function

import argparse
import logging
import multiprocessing
import os
import subprocess
import sys

from git import Repo

import environment

from support import buildsystem, deps


def build(arch, package):
    subprocess.check_call(['python', './buildPackages.py', '--target', arch,
                           '--only-depends', package])


def main(argv):
    parser = argparse.ArgumentParser(description='Build ports in parallel.')
    parser.add_argument('--jobs', type=int,
                        default=max(multiprocessing.cpu_count() / 2, 1),
                        help='Number of parallel builds to perform.')
    parser.add_argument('--arch', type=str, choices=('amd64', 'arm'),
                        default='amd64', help='Architecture to build for.')
    args = parser.parse_args()

    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    logging.info('running with %d jobs', args.jobs)

    pool = multiprocessing.Pool(processes=args.jobs)

    # Collect dependencies to find roots from which we can run full builds.

    # Architecture should make no impact on the package listing.
    env = environment.generate_environment(args.arch)

    # Load packages.
    packages = buildsystem.load_packages(env)

    # Trim packages not in source control.
    repo = Repo()
    head = repo.head.commit.tree
    for key in packages.keys()[:]:
        if 'packages/%s' % (key,) not in head['packages']:
            del packages[key]

    jobs = []
    for package in deps.get_final_packages(packages):
        jobs.append(pool.apply_async(build, (args.arch, package)))

    for job in jobs:
        try:
            job.get()
        except:
            logging.exception('build failed')

    return 0


if __name__ == '__main__':
    exit(main(sys.argv))
