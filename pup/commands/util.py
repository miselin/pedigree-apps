
import logging
import os
import sqlite3

try:
    from ConfigParser import SafeConfigParser
except ImportError:
    from configparser import SafeConfigParser


log = logging.getLogger(__name__)


def SqliteDictFactory(cursor, row):
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


class PupConfig(object):

    def __init__(self, repo_urls, local_cache, install_root, architecture):
        self.repo_urls = repo_urls
        self.local_cache = local_cache
        self.install_root = install_root
        self.architecture = architecture
        self.db_path = os.path.join(self.local_cache, 'packages.pupdb')
        log.debug('loading database from %s', self.db_path)
        self.db = sqlite3.connect(self.db_path)
        self.db.row_factory = SqliteDictFactory

        if not os.path.isdir(self.local_cache):
            os.makedirs(self.local_cache)
        if not os.path.isdir(self.install_root):
            os.makedirs(self.install_root)


def load_config(args):
    pup_config = args.config
    if pup_config is None:
        pup_config = '/support/pup/pup.conf'

    # Slurp the config file.
    parser = SafeConfigParser()
    parser.read(pup_config)

    repos = [server[1] for server in parser.items("remotes")]

    return PupConfig(
        repos,
        parser.get("paths", "localdb"),
        parser.get("paths", "installroot"),
        parser.get("settings", "arch"),
    )
