import pathlib
import unittest

from .package import SedPackage


class SedPackageTest(unittest.TestCase):
    def test_gnulib_tests_use_the_existing_musl_locale_name_path(self):
        package = SedPackage(__file__)
        self.assertEqual(
            package.patches({}, "/source"),
            ["pselect-null.diff", "pedigree-musl-locale.diff"],
        )

        patch = (
            pathlib.Path(__file__).parent
            / "patches"
            / "pedigree-musl-locale.diff"
        ).read_text(encoding="utf-8")
        self.assertIn("defined __linux__ || defined __pedigree__", patch)
        self.assertIn("NL_LOCALE_NAME", patch)


if __name__ == "__main__":
    unittest.main()
