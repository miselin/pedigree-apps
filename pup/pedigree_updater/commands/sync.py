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
import urllib
import shutil

from . import base
from pedigree_updater.lib import util


log = logging.getLogger(__name__)


class SyncCommand(base.PupCommand):

    def name(self):
        return 'sync'

    def help(self):
        return 'sync package database'

    def add_arguments(self, parser):
        pass

    def run(self, args, config):
        if not os.path.isdir(config.local_cache):
            os.makedirs(config.local_cache)

        new_database = os.path.join(config.local_cache, 'packages_new.pupdb')
        target_database = os.path.join(config.local_cache, 'packages.pupdb')

        banned_repos = set()
        for repo in config.repo_urls:
            if repo in banned_repos:
                log.warn('ignoring repo %s, it has failed previously', repo)
                continue

            with open(new_database, 'wb') as t:
                remote_url = '%s/packages.pupdb' % repo
                try:
                    log.info('trying %s', remote_url)
                    f = urllib.urlopen(remote_url)
                    log.info('%s is OK', remote_url)
                except:
                    banned_repos.add(repo)
                    continue

                shutil.copyfileobj(f, t)
                f.close()

        if not os.path.isfile(new_database):
            print('Could not download updated database from server.')
            return 1

        # If we didn't have a database before, reload config
        have_db = os.path.exists(target_database)
        if config.created:
            log.info('overwriting newly-created database with synced database')
            have_db = False
        if not have_db:
            os.rename(new_database, target_database)
            new_database = target_database

            config = util.load_config(args)

        # Drop in place if we had a database previously, we've now verified
        # the new database.
        if have_db:
            os.rename(new_database, target_database)

        print('Synchronisation complete.')
