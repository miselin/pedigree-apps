#!/usr/bin/env python
'''
    PUP: Pedigree UPdater

    Copyright (c) 2010 Matthew Iselin

    Permission to use, copy, modify, and distribute this software for any
    purpose with or without fee is hereby granted, provided that the above
    copyright notice and this permission notice appear in all copies.

    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
    ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
    OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

    pup-install.py: install a package
'''

import hashlib
import logging
import os
import sys
import urllib
import sqlite3
import tarfile

from . import base
from . import schema
from . import util


log = logging.getLogger(__name__)


class InstallCommand(base.PupCommand):

    def name(self):
        return 'install'

    def help(self):
        return 'install packages'

    def add_arguments(self, parser):
        parser.add_argument('package', nargs='+', type=str,
            help='packages to install')
        parser.add_argument('--nodeps', action='store_true',
            help='ignore package dependencies (not recommended)')

    def run(self, args, config):
        # Do all the given packages exist?
        packages = []
        for package in args.package:
            e = config.db.execute('SELECT * FROM packages WHERE name=? AND '
                'architecture=? ORDER BY version DESC',
                (package, config.architecture))
            result = e.fetchone()
            if result is None:
                print('The package "%s" is not available. Try running `pup sync`?' % package)
                return 1

            # TODO(miselin): extract dependencies?

            packages.append(result)

        # OK, good to go.
        print('Installing %d packages...' % len(packages))

        banned_repos = set()
        for package in packages:
            package_name = '%(name)s-%(version)s-%(architecture)s' % package
            package_file = os.path.join(config.local_cache, '%s.pup' % package_name)

            package_sha1 = package['sha1']
            download = True
            if os.path.isfile(package_file):
                # Do we need to download again?
                h = hashlib.sha1()
                with open(package_file) as f:
                    h.update(f.read())

                download = package_sha1 != h.hexdigest()

            if download:
                log.info('package %s needs to be downloaded', package['name'])
                for repo in config.repo_urls:
                    if repo in banned_repos:
                        log.warn('ignoring repo %s, it has failed previously',
                            repo)

                    with open(package_file, 'wb') as t:
                        remote_url = '%s/%s.pup' % (repo, package_name)
                        try:
                            f = urllib.urlopen(remote_url)
                        except:
                            banned_repos.add(repo)
                            continue

                        shutil.copyfileobj(f, t)
                        f.close()

            if not os.path.isfile(package_file):
                print('Could not download package "%s" from server.' % package['name'])
                return 1

            # Install.
            t = tarfile.open(package_file)
            t.extractall(config.install_root)

            print('Package "%s" is now installed.' % package['name'])
