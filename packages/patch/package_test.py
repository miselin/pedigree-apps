import unittest

from .package import PatchPackage


class PatchPackageTest(unittest.TestCase):
    def test_is_standalone_with_no_runtime_dependencies(self):
        package = PatchPackage(__file__)

        self.assertEqual(package.name(), "patch")
        self.assertEqual(package.version(), "2.8")
        self.assertEqual(package.build_requires(), [])
        self.assertEqual(package.install_deps(), [])
        self.assertEqual(package.patches({}, "/source"), [])


if __name__ == "__main__":
    unittest.main()
