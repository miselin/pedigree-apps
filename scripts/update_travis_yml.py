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
        'python': '2.7',
        'services': ['docker'],
        'env': [
            'TARGET=%(target)s',
            'PACKAGE=%(package)s',
            'CC=clang',
            'CXX=clang++',
            {'secure': 'W9NNuKNiJf+vx1QR3K4Cyt3yBgRKRO2Raqt8szG5uryyRX777uqD7+'
                       'mxekWJEsTdR7gQHStKXEZwA9tNnCQusN09gd8VG7j1RxxlyrjM3HNt'
                       '0qwyFbZNrbIMKxBV2K2Y6lSljLm3DQd7yO9799rnlo9q6jygg/zhyM'
                       'bfLlIshgA='},
        ],
    }

    if 'matrix' not in data:
        data['matrix'] = {}

    # Wipe out existing data so we can correctly fill our packages.
    data['matrix']['include'] = []
    data['matrix']['allow_failures'] = []

    matrix_include = data['matrix']['include']
    matrix_allow_failures = data['matrix']['allow_failures']

    for package in deps.get_final_packages(packages):
        for target in ('amd64', 'arm'):
            copy = base_include.copy()

            def fix(x):
                if isinstance(x, str):
                    return x % {
                        'package': package,
                        'target': target,
                    }
                else:
                    return x

            copy['env'] = [fix(x) for x in copy['env']]

            matrix_include.append(copy)
            matrix_allow_failures.append(copy)

    with open('.travis.yml', 'w') as f:
        yaml.safe_dump(data, f, default_flow_style=False)


if __name__ == '__main__':
    main()
