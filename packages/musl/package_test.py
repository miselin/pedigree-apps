import unittest

from .package import MuslPackage


class MuslPackageTest(unittest.TestCase):
    def test_matches_kernel_target_derivation(self):
        package = MuslPackage(__file__)

        self.assertEqual(package.name(), "musl")
        self.assertEqual(package.version(), "1.2.6")
        self.assertEqual(
            package.patches({}, ""),
            [
                "musl-1.2.6-cve-2026-40200-qsort.patch",
                "musl-1.2.6-cve-2026-6042-iconv.patch",
            ],
        )
        self.assertEqual(package.build_requires(), [])
        self.assertEqual(package.install_deps(), [])


if __name__ == "__main__":
    unittest.main()
