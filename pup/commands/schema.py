
import logging


log = logging.getLogger(__name__)


class PupSchema(object):
    """Pup database schema management."""

    def __init__(self, db):
        cursor = db.execute('PRAGMA user_version;')
        self._version = cursor.fetchone().get('user_version', 0)
        self._db = db

    def latest_version(self):
        return 1

    def upgrade(self):
        if self._version >= self.latest_version():
            log.debug('nothing to be done in schema upgrade')
            return

        for i in range(self._version + 1, self.latest_version() + 1):
            log.debug('schema upgrading to version %d', i)
            upgrade = '_upgrade_to_%d' % i
            fn = getattr(self, upgrade)
            fn(self._db)

        self._version = i
        self._db.execute('PRAGMA user_version = %d' % i)

    def _upgrade_to_1(self, db):
        db.execute('DROP TABLE IF EXISTS packages')
        db.execute('''
CREATE TABLE packages (
    package_id integer PRIMARY KEY AUTOINCREMENT,
    name text(256),
    version text(64),
    dependencies text(4096),
    sha1 text(42),
    architecture text(64)
);''')
