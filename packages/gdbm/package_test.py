import unittest

from .package import GdbmPackage


class GdbmPackageTest(unittest.TestCase):
    def test_no_legacy_timing_workaround_is_applied(self):
        self.assertEqual(GdbmPackage(__file__).patches({}, ""), [])


if __name__ == "__main__":
    unittest.main()
