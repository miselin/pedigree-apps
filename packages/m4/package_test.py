import os
import unittest

from .package import m4Package


class M4PackageTest(unittest.TestCase):
    def test_pedigree_uses_the_existing_musl_locale_name_path(self):
        package = m4Package(__file__)

        self.assertEqual(
            package.patches({}, "/source"),
            ["pselect-null.diff", "pedigree-musl-locale.diff"],
        )

        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "pedigree-musl-locale.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        platform_gate = "(defined __linux__ || defined __pedigree__)"
        self.assertEqual(patch.count(platform_gate), 2)
        self.assertIn(
            "|| (" + platform_gate + " && HAVE_LANGINFO_H)", patch
        )
        self.assertIn(
            "+#elif " + platform_gate
            + " && HAVE_LANGINFO_H && defined NL_LOCALE_NAME",
            patch,
        )
        self.assertEqual(patch.count("diff --git "), 1)


if __name__ == "__main__":
    unittest.main()
