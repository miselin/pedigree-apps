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
import urllib
import shutil
import tarfile

from . import base


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
                            help='ignore any package dependencies '
                                 '(not recommended)')

    def run(self, args, config):
        if not os.path.isdir(config.install_root):
            os.makedirs(config.install_root)

        # Do all the given packages exist?
        packages = []
        for package in args.package:
            desired = '%s-%s' % (package, config.architecture)

            if desired not in config.db:
                print('The package "%s" is not available. Try running '
                      ' `pup sync`?' % package)
                return 1

            # TODO(miselin): extract dependencies?

            packages.append(config.db[desired])

        # OK, good to go.
        print('Installing %d packages...' % len(packages))

        banned_repos = set()
        for package in packages:
            package_name = '%(name)s-%(version)s-%(architecture)s' % package
            pup_filename = '%s.pup' % package_name
            package_file = os.path.join(config.local_cache, pup_filename)

            package_sha1 = package['sha1']
            download = True
            if os.path.isfile(package_file):
                # Do we need to download again?
                h = hashlib.sha1()
                with open(package_file, 'rb') as f:
                    h.update(f.read())

                download = package_sha1 != h.hexdigest()

            if download:
                log.info('package %s needs to be downloaded', package['name'])
                for repo in config.repo_urls:
                    if repo in banned_repos:
                        log.warn('ignoring repo %s, it has failed previously',
                                 repo)
                        continue

                    with open(package_file, 'wb') as t:
                        remote_url = '%s/%s' % (repo, pup_filename)
                        try:
                            f = urllib.urlopen(remote_url)
                        except:
                            banned_repos.add(repo)
                            continue

                        shutil.copyfileobj(f, t)
                        f.close()

            if not os.path.isfile(package_file):
                print('Could not download package "%s" from server.' % (
                      package['name'],))
                return 1

            # Install.
            t = tarfile.open(package_file)
            t.extractall(config.install_root)

            print('Package "%s" is now installed.' % package['name'])
