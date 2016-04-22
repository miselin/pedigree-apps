
import logging
import os

try:
    import simplejson as json
except ImportError:
    import json

try:
    from ConfigParser import SafeConfigParser, NoOptionError
except ImportError:
    from configparser import SafeConfigParser, NoOptionError


log = logging.getLogger(__name__)


def SqliteDictFactory(cursor, row):
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


class PupConfig(object):

    def __init__(self, repo_urls, local_cache, install_root, architecture,
                 upload_url):
        self.repo_urls = repo_urls
        self.upload_url = upload_url
        self.local_cache = local_cache
        self.install_root = install_root
        self.architecture = architecture
        self.db = {}
        self.db_path = os.path.join(self.local_cache, 'packages.pupdb')
        if os.path.exists(self.db_path):
            log.debug('loading database from %s', self.db_path)
            self.created = False
        else:
            log.info('database does not yet exist at %s', self.db_path)
            self.created = True

            # Make sure the intermediate directories exist first.
            parent_dir = os.path.dirname(os.path.abspath(self.db_path))
            if not os.path.isdir(parent_dir):
                os.makedirs(parent_dir)

            # Write an empty JSON file.
            with open(self.db_path, 'w') as f:
                f.write('{}')

        try:
            with open(self.db_path) as f:
                self.db = json.load(f)
        except ValueError:
            log.warning('failed to load database, you should sync')
            self.db = {}

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
        repos = [server[1] for server in parser.items('remotes')
                 if server[0] == 'server']
        try:
            upload_url = parser.get('remotes', 'upload')
        except NoOptionError:
            upload_url = ''
    else:
        repos = []
        upload_url = ''

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
        architecture,
        upload_url,
    )
