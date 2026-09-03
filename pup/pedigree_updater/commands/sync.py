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

import json
import logging
import os
import tempfile
from pathlib import Path

from . import base
from ..lib import http as pup_http
from ..lib import util

log = logging.getLogger(__name__)


def _valid_package_database(path):
    try:
        with open(path, encoding="utf-8") as database_file:
            database = json.load(database_file)
    except (OSError, UnicodeDecodeError, ValueError):
        return False

    if not isinstance(database, dict):
        return False

    required_fields = ("name", "version", "architecture", "sha1")
    for key, package in database.items():
        if not isinstance(key, str) or not isinstance(package, dict):
            return False
        if any(
            not isinstance(package.get(field), str) or not package[field]
            for field in required_fields
        ):
            return False
        dependencies = package.get("dependencies", [])
        if not isinstance(dependencies, list) or any(
            not isinstance(dependency, str) or not dependency
            for dependency in dependencies
        ):
            return False
        if key != "%s-%s" % (package["name"], package["architecture"]):
            return False

    return True


class SyncCommand(base.PupCommand):
    def name(self):
        return "sync"

    def help(self):
        return "sync package database"

    def add_arguments(self, parser):
        pass

    def run(self, args, config):
        if not os.path.isdir(config.local_cache):
            os.makedirs(config.local_cache)

        new_database = os.path.join(config.local_cache, "packages_new.pupdb")
        target_database = os.path.join(config.local_cache, "packages.pupdb")
        Path(new_database).unlink(missing_ok=True)

        banned_repos = set()

        for repo in config.repo_urls:
            if repo in banned_repos:
                log.warning("ignoring repo %s; it failed previously", repo)
                continue

            remote_url = f"{repo.rstrip('/')}/packages.pupdb"
            temporary_path = None

            try:
                log.info("trying %s", remote_url)

                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=os.path.dirname(new_database),
                    delete=False,
                ) as target:
                    temporary_path = target.name
                    pup_http.copy_url(remote_url, target)

                if not _valid_package_database(temporary_path):
                    log.warning(
                        "repo returned an invalid package database: %s", repo
                    )
                    Path(temporary_path).unlink(missing_ok=True)
                    banned_repos.add(repo)
                    continue

                os.replace(temporary_path, new_database)
                log.info("%s is OK", remote_url)
                break

            except (pup_http.RequestError, OSError):
                if temporary_path:
                    Path(temporary_path).unlink(missing_ok=True)
                log.exception("repo failed: %s", repo)
                banned_repos.add(repo)

        if not os.path.isfile(new_database):
            print("Could not download updated database from server.")
            return 1

        # If we didn't have a database before, reload config
        have_db = os.path.exists(target_database)
        if config.created:
            log.info("overwriting newly-created database with synced database")
            have_db = False
        if not have_db:
            os.replace(new_database, target_database)
            new_database = target_database

            config = util.load_config(args)

        # Drop in place if we had a database previously, we've now verified
        # the new database.
        if have_db:
            os.replace(new_database, target_database)

        print("Synchronisation complete.")
