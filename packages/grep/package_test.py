import pathlib
import unittest

from .package import GrepPackage


class GrepPackageTest(unittest.TestCase):
    def test_gnulib_tests_use_the_existing_musl_locale_name_path(self):
        patch_path = pathlib.Path(__file__).parent / "patches" / (
            "pedigree-musl-locale.diff"
        )
        patch = patch_path.read_text(encoding="utf-8")

        self.assertIn("defined __linux__ || defined __pedigree__", patch)
        self.assertIn("NL_LOCALE_NAME", patch)


if __name__ == "__main__":
    unittest.main()
