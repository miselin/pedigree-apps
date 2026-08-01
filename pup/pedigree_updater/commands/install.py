#!/usr/bin/env python3
"""
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
"""

import hashlib
import logging
import os
import shutil
import tarfile
from pathlib import Path

import requests

from . import base

log = logging.getLogger(__name__)


class InstallCommand(base.PupCommand):
    def name(self):
        return "install"

    def help(self):
        return "install packages"

    def add_arguments(self, parser):
        parser.add_argument("package", nargs="+", type=str, help="packages to install")
        parser.add_argument(
            "--nodeps",
            action="store_true",
            help="ignore any package dependencies (not recommended)",
        )

    def run(self, args, config):
        if not os.path.isdir(config.install_root):
            os.makedirs(config.install_root)

        # Do all the given packages exist?
        packages = []
        for package in args.package:
            desired = f"{package}-{config.architecture}"

            if desired not in config.db:
                print(
                    f'The package "{package}" is not available. Try running '
                    " `pup sync`?"
                )
                return 1

            # TODO(miselin): extract dependencies?

            packages.append(config.db[desired])

        # OK, good to go.
        print(f"Installing {len(packages)} packages...")

        banned_repos = set()
        for package in packages:
            package_name = "{name}-{version}-{architecture}".format(**package)
            pup_filename = f"{package_name}.pup"
            package_file = os.path.join(config.local_cache, pup_filename)

            package_sha1 = package["sha1"]
            download = True
            if os.path.isfile(package_file):
                # Do we need to download again?
                h = hashlib.sha1()
                with open(package_file, "rb") as f:
                    h.update(f.read())

                download = package_sha1 != h.hexdigest()

            if download:
                log.info("package %s needs to be downloaded", package["name"])
                for repo in config.repo_urls:
                    if repo in banned_repos:
                        log.warning("ignoring repo %s, it has failed previously", repo)
                        continue

                    remote_url = f"{repo.rstrip('/')}/{pup_filename}"

                    try:
                        with requests.get(
                            remote_url,
                            stream=True,
                            timeout=(5, 60),
                            headers={"User-Agent": "pup-client/1.0"},
                        ) as response:
                            response.raise_for_status()
                            response.raw.decode_content = True

                            with open(package_file, "wb") as target:
                                shutil.copyfileobj(response.raw, target)

                    except requests.RequestException:
                        Path(package_file).unlink(missing_ok=True)
                        banned_repos.add(repo)
                        continue

            if not os.path.isfile(package_file):
                print(
                    'Could not download package "{}" from server.'.format(
                        package["name"]
                    )
                )
                return 1

            # Install.
            with tarfile.open(package_file) as t:
                t.extractall(config.install_root)

            print('Package "{}" is now installed.'.format(package["name"]))
