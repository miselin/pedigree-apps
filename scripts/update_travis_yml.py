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

    secure = {
        'secure': 'ZiZk/cKj4PXaxpOt0AxJ2raY5tB43NBDGPO92pTsXO01rJvn/'
                  '1T7sUkrT3DUWjsCH7itfqdGJCau5IGZdD8Vdsji0PcH4va1koaYW/'
                  '4lLBT5cq2GxaQdkminSP2aEXBSrLV9/PdsP7wdcgL7PqW0/'
                  'OeDaM0tF+gxOcWNmBz3dKg=',
    }

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
            secure,
        ],
    }

    if 'matrix' not in data:
        data['matrix'] = {}

    # Wipe out existing data so we can correctly fill our packages.
    data['matrix']['include'] = []
    data['matrix']['allow_failures'] = []

    matrix_include = data['matrix']['include']
    matrix_allow_failures = data['matrix']['allow_failures']

    # Add the dependency upload builds.
    for target in ('amd64', 'arm'):
        build = {
            'os': 'linux',
            'python': '2.7',
            'env': [
                'DEPS_ONLY=y',
                'TARGET=' + target,
                secure,
            ]
        }
        matrix_include.append(build)

    # Disabled for now.
    for package, _ in []:  # deps.sort_dependencies(packages):
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
