import pathlib
import unittest

from .package import GrepPackage


class GrepPackageTest(unittest.TestCase):
    def test_fifo_drain_requires_configured_splice(self):
        package = GrepPackage(__file__)

        self.assertEqual(
            package.patches({}, "/source"),
            [
                "pselect-null.diff",
                "pedigree-no-splice.diff",
                "pedigree-musl-locale.diff",
            ],
        )

        patch_path = pathlib.Path(__file__).parent / "patches" / (
            "pedigree-no-splice.diff"
        )
        patch = patch_path.read_text(encoding="utf-8")

        self.assertIn(
            "+#if defined SPLICE_F_MOVE && HAVE_SPLICE",
            patch,
        )
        self.assertNotIn("+#ifdef SPLICE_F_MOVE", patch)

    def test_gnulib_tests_use_the_existing_musl_locale_name_path(self):
        patch_path = pathlib.Path(__file__).parent / "patches" / (
            "pedigree-musl-locale.diff"
        )
        patch = patch_path.read_text(encoding="utf-8")

        self.assertIn("defined __linux__ || defined __pedigree__", patch)
        self.assertIn("NL_LOCALE_NAME", patch)


if __name__ == "__main__":
    unittest.main()
