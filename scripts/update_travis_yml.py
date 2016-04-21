#!/usr/bin/env python
# -*- python -*-

from __future__ import print_function

import os
import yaml

from git import Repo

import environment

from support import buildsystem, deps


def main():
    if not os.path.exists('.travis.yml'):
        print('.travis.yml must exist in the working directory.')
        exit(1)

    # Architecture should make no impact on the package listing.
    env = environment.generate_environment('amd64')

    # Load packages.
    packages = buildsystem.load_packages(env)

    # Trim packages not in source control.
    repo = Repo()
    head = repo.head.commit.tree
    for key in packages.keys()[:]:
        if 'packages/%s' % (key,) not in head['packages']:
            del packages[key]

    with open('.travis.yml') as f:
        data = yaml.safe_load(f)

    # Update the includes section.
    base_include = {
        'os': 'linux',
        'sudo': True,
        'compiler': 'gcc',
        'python': '2.7',
        'env': 'TARGET=amd64 PACKAGE=%s',
    }

    if 'matrix' not in data:
        data['matrix'] = {'include': []}

    # Wipe out existing data so we can correctly fill our packages.
    data['matrix']['include'] = []

    matrix_include = data['matrix']['include']

    for package in deps.get_final_packages(packages):
        copy = base_include.copy()
        copy['env'] = copy['env'] % package

        matrix_include.append(copy)

    with open('.travis.yml', 'w') as f:
        yaml.safe_dump(data, f, default_flow_style=False)


if __name__ == '__main__':
    main()
