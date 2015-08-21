
import logging
import os
import sqlite3

try:
    from ConfigParser import SafeConfigParser
except ImportError:
    from configparser import SafeConfigParser

from . import schema


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
        if os.path.exists(self.db_path):
            log.debug('loading database from %s', self.db_path)
            self.db = sqlite3.connect(self.db_path)
            self.db.row_factory = SqliteDictFactory
            self.schema = schema.PupSchema(self.db)
        else:
            self.db = None

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

    if parser.has_section('remotes'):
        repos = [server[1] for server in parser.items('remotes')]
    else:
        repos = []

    if parser.has_section('paths'):
        local_cache = parser.get('paths', 'localdb')
        install_root = parser.get('paths', 'installroot')
    else:
        local_cache = '/support/pup/db'
        install_root = '/'

    if parser.has_section('settings'):
        architecture = parser.get('settings', 'arch')
    else:
        architecture = 'amd64'

    return PupConfig(
        repos,
        local_cache,
        install_root,
        architecture
    )
