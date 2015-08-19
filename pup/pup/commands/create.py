#!/usr/bin/env python
'''
PUP: Pedigree UPdater

Copyright (c) 2015 Matthew Iselin

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
'''

import logging
import os
import tarfile

from . import base


log = logging.getLogger(__name__)


class CreatePackageCommand(base.PupCommand):

    def name(self):
        return 'create'

    def help(self):
        return 'create package'

    def add_arguments(self, parser):
        parser.add_argument('--package', type=str, required=True,
                            help='name of the package to create')
        parser.add_argument('--version', type=str, required=True,
                            help='version of the package to create')
        parser.add_argument('--architecture', type=str, required=True,
                            choices=('amd64', 'arm'),
                            help='architecture of the package to create')
        parser.add_argument('--path', type=str, required=True,
                            help='base path for package directory structure')

    def run(self, args, config):
        if not os.path.isdir(config.local_cache):
            os.makedirs(config.local_cache)

        package_name = '%s-%s-%s' % (args.package, args.version,
                                     args.architecture)
        pup_filename = '%s.pup' % package_name
        package_file = os.path.join(config.local_cache, pup_filename)
        log.info('create package %s [%s]', package_name, package_file)

        if not os.path.isdir(args.path):
            print('Package path "%s" does not exist or is not a directory.' % (
                args.path,))
            return 1

        entries = [os.path.join(args.path, x) for x in os.listdir(args.path)]
        if not entries:
            print('Package path "%s" is empty.' % args.path)
            return 1

        tar = tarfile.open(package_file, 'w:gz')
        for entry in entries:
            log.debug('%s: add "%s"' % (package_name, entry))
            tar.add(entry, arcname=os.path.basename(entry))
        tar.close()

        print('Package "%s" is now created at %s.' % (package_name,
                                                      package_file))
        print('Run `pup register --package=%s --version=%s --architecture=%s` '
              'to register this package in the local repository.' % (
                  args.package, args.version, args.architecture))
