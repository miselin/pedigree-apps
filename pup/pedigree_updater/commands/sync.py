#!/usr/bin/env python
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
import shutil
import tempfile

import requests
from pedigree_updater.lib import util

from . import base

log = logging.getLogger(__name__)


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

        banned_repos = set()

        for repo in config.repo_urls:
            if repo in banned_repos:
                log.warning("ignoring repo %s; it failed previously", repo)
                continue

            remote_url = f"{repo.rstrip('/')}/packages.pupdb"

            try:
                log.info("trying %s", remote_url)

                with requests.get(
                    remote_url,
                    stream=True,
                    timeout=(5, 60),
                    headers={"User-Agent": "pup-client/1.0"},
                ) as response:
                    response.raise_for_status()
                    response.raw.decode_content = True

                    log.info("%s is OK", remote_url)

                    with tempfile.NamedTemporaryFile(
                        mode="wb",
                        dir=os.path.dirname(new_database),
                        delete=False,
                    ) as target:
                        shutil.copyfileobj(response.raw, target)
                        temporary_path = target.name

                os.replace(temporary_path, new_database)
                break

            except (requests.RequestException, OSError):
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
            os.rename(new_database, target_database)
            new_database = target_database

            config = util.load_config(args)

        # Drop in place if we had a database previously, we've now verified
        # the new database.
        if have_db:
            os.rename(new_database, target_database)

        print("Synchronisation complete.")
