#!/usr/bin/env python3
"""
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
"""

import logging
import os
import tarfile

from . import base

log = logging.getLogger(__name__)


class CreatePackageCommand(base.PupCommand):
    def name(self):
        return "create"

    def help(self):
        return "create package"

    def add_arguments(self, parser):
        parser.add_argument(
            "--package", type=str, required=True, help="name of the package to create"
        )
        parser.add_argument(
            "--version",
            type=str,
            required=True,
            help="version of the package to create",
        )
        parser.add_argument(
            "--architecture",
            type=str,
            required=True,
            choices=("amd64", "arm"),
            help="architecture of the package to create",
        )
        parser.add_argument(
            "--path",
            type=str,
            required=True,
            help="base path for package directory structure",
        )

    def run(self, args, config):
        if not os.path.isdir(config.local_cache):
            os.makedirs(config.local_cache)

        package_name = f"{args.package}-{args.version}-{args.architecture}"
        pup_filename = f"{package_name}.pup"
        package_file = os.path.join(config.local_cache, pup_filename)
        log.info("create package %s [%s]", package_name, package_file)

        if not os.path.isdir(args.path):
            print(f'Package path "{args.path}" does not exist or is not a directory.')
            return 1

        entries = [os.path.join(args.path, x) for x in os.listdir(args.path)]
        if not entries:
            print(f'Package path "{args.path}" is empty.')
            return 1

        with tarfile.open(package_file, "w:gz") as tar:
            for entry in entries:
                log.debug(f'{package_name}: add "{entry}"')
                tar.add(entry, arcname=os.path.basename(entry))

        print(f'Package "{package_name}" is now created at {package_file}.')
        print(
            f"Run `pup register --package={args.package} --version={args.version} --architecture={args.architecture}` "
            "to register this package in the local repository."
        )
