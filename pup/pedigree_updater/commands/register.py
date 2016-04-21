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

import base64
import hashlib
import logging
import os
import urllib

from . import base


log = logging.getLogger(__name__)


class RegisterPackageCommand(base.PupCommand):

    def name(self):
        return 'register'

    def help(self):
        return 'register packages'

    def add_arguments(self, parser):
        parser.add_argument('--package', type=str, required=True,
                            help='name of the package to register')
        parser.add_argument('--version', type=str, required=True,
                            help='version of the package to register')
        parser.add_argument('--architecture', type=str, required=True,
                            choices=('amd64', 'arm'),
                            help='architecture of the package to register')
        parser.add_argument('--key', type=str, required=True,
                            help='Upload key for the repository')
        parser.add_argument('dependency', nargs='*', type=str,
                            help='packages this package should depend on')

    def run(self, args, config):
        package_name = '%s-%s-%s' % (args.package, args.version,
                                     args.architecture)
        pup_filename = '%s.pup' % package_name
        package_file = os.path.join(config.local_cache, pup_filename)
        if not os.path.isfile(package_file):
            print('No file exists for package %s.', package_file)
            return 1

        log.info('register package %s [%s]', package_name, package_file)

        with open(package_file, 'rb') as f:
            contents = f.read()

        postdata = {
            'name': args.package,
            'vers': args.version,
            'arch': args.architecture,
            'blob': base64.b64encode(contents),
            'key': 'upload',
            'key_value': args.key,
        }
        postdata = urllib.urlencode(postdata)

        url = '%s/upload' % (config.upload_url,)
        if not url:
            print('No upload URL is configured in the config file.')
            return 1

        response = urllib.urlopen(url, postdata)

        result = response.read()
        if result != 'ok':
            print('Registering package "%s" failed: %s' % (package_name,
                                                           result))
            return 1
        else:
            print('Package "%s" has been registered.' % package_name)
