import unittest

from .package import GzipPackage


class GzipPackageTest(unittest.TestCase):
    def test_helper_scripts_use_the_target_base_shell(self):
        self.assertEqual(GzipPackage(__file__).install_deps(), [])


if __name__ == "__main__":
    unittest.main()
