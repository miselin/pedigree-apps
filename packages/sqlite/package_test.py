import os
import unittest

from .package import Sqlite


class SqlitePackageTest(unittest.TestCase):
    def test_no_legacy_cli_syscall_workaround_is_applied(self):
        self.assertEqual(Sqlite(__file__).patches({}, ""), [])


if __name__ == "__main__":
    unittest.main()
