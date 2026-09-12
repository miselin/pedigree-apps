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
import sys
import tarfile
import tempfile
from collections import defaultdict
from pathlib import Path

from . import base
from ..lib import http as pup_http

log = logging.getLogger(__name__)


class PackageResolutionError(Exception):
    pass


class InstallTarFile(tarfile.TarFile):
    def makefile(self, tarinfo, targetpath):
        # Running programs retain the old inode, including pages faulted later.
        # Publish only after the replacement has been completely written.
        fd, temporary = tempfile.mkstemp(prefix=".pup-", dir=os.path.dirname(targetpath))
        os.close(fd)
        try:
            super().makefile(tarinfo, temporary)
            self.chown(tarinfo, temporary, numeric_owner=False)
            self.chmod(tarinfo, temporary)
            self.utime(tarinfo, temporary)
            os.replace(temporary, targetpath)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)


def _resolve_packages(package_names, database, architecture, include_dependencies):
    """Build a stable, dependency-first installation plan."""
    packages = []
    states = {}
    stack = []

    def visit(package_name, required_by=None):
        package_key = f"{package_name}-{architecture}"
        package = database.get(package_key)
        if package is None:
            if required_by is None:
                raise PackageResolutionError(
                    f'The package "{package_name}" is not available. Try running '
                    "`pup sync`?"
                )
            raise PackageResolutionError(
                f'The dependency "{package_name}" required by "{required_by}" '
                f'is not available for architecture "{architecture}". Try running '
                "`pup sync`?"
            )

        state = states.get(package_key)
        if state == "resolved":
            return
        if state == "resolving":
            cycle_start = stack.index(package_key)
            cycle = stack[cycle_start:] + [package_key]
            cycle_names = [database[key]["name"] for key in cycle]
            raise PackageResolutionError(
                "Dependency cycle detected: {}.".format(" -> ".join(cycle_names))
            )

        states[package_key] = "resolving"
        stack.append(package_key)
        if include_dependencies:
            for dependency in package.get("dependencies", []):
                visit(dependency, package["name"])
        stack.pop()
        states[package_key] = "resolved"
        packages.append(package)

    for package_name in package_names:
        visit(package_name)

    return packages


def _package_matches_sha1(path, expected):
    digest = hashlib.sha1()
    with open(path, "rb") as package:
        while True:
            chunk = package.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest() == expected


def macos_safe_members(tar, log):
    """Calculate the list of allowed files to extract that works on a case-insensitive FS"""
    groups = defaultdict(list)

    for member in tar.getmembers():
        key = os.path.normpath(member.name).casefold()
        groups[key].append(member)

    allowed = []

    for members in groups.values():
        if len(members) == 1:
            allowed.append(members[0])
            continue

        # Prefer an actual file/directory over a symlink.
        chosen = next((m for m in members if not (m.issym() or m.islnk())), members[0])
        skipped = [m.name for m in members if m is not chosen]

        log.critical(
            "PACKAGE INSTALL DEGRADED: case-insensitive filesystem collision; "
            "keeping %r and skipping %r",
            chosen.name,
            skipped,
        )
        allowed.append(chosen)

    return allowed


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

        try:
            packages = _resolve_packages(
                args.package,
                config.db,
                config.architecture,
                include_dependencies=not args.nodeps,
            )
        except PackageResolutionError as error:
            print(error)
            return 1

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
                download = not _package_matches_sha1(package_file, package_sha1)

            if download:
                Path(package_file).unlink(missing_ok=True)
                log.info("package %s needs to be downloaded", package["name"])
                for repo in config.repo_urls:
                    if repo in banned_repos:
                        log.warning("ignoring repo %s, it has failed previously", repo)
                        continue

                    remote_url = f"{repo.rstrip('/')}/{pup_filename}"

                    try:
                        with open(package_file, "wb") as target:
                            pup_http.copy_url(remote_url, target)
                        if not _package_matches_sha1(package_file, package_sha1):
                            log.warning(
                                "package %s from %s failed its SHA-1 check",
                                package["name"],
                                repo,
                            )
                            Path(package_file).unlink(missing_ok=True)
                            banned_repos.add(repo)
                            continue
                    except (pup_http.RequestError, OSError):
                        Path(package_file).unlink(missing_ok=True)
                        banned_repos.add(repo)
                        continue
                    break

            if not os.path.isfile(package_file):
                print(
                    'Could not download package "{}" from server.'.format(
                        package["name"]
                    )
                )
                return 1

            # Install.
            with InstallTarFile.open(package_file) as t:
                members = (
                    macos_safe_members(t, log) if sys.platform == "darwin" else None
                )

                t.extractall(config.install_root, members=members)

            print('Package "{}" is now installed.'.format(package["name"]))
