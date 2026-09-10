import os
import unittest

from .package import e2fsprogsPackage


class E2fsprogsPackageTest(unittest.TestCase):
    def test_no_legacy_positional_io_workaround_is_applied(self):
        self.assertEqual(e2fsprogsPackage(__file__).patches({}, ""), [])


if __name__ == "__main__":
    unittest.main()
