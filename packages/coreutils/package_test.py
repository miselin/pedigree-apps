import os
import unittest
from unittest import mock

from .package import CoreutilsPackage


class CoreutilsPackageTest(unittest.TestCase):
    @mock.patch("packages.coreutils.package.steps.run_configure")
    def test_configure_disables_staged_dependency_rpaths(self, run_configure):
        CoreutilsPackage(__file__).configure({}, "/source")

        self.assertIn(
            "--disable-rpath",
            run_configure.call_args.kwargs["extra_config"],
        )

    def test_pedigree_uses_the_existing_musl_locale_name_path(self):
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
        self.assertIn(
            "@@ -465,7 +465,7 @@ getlocalename_l_unsafe "
            "(int category, locale_t locale)\n"
            "            nl_langinfo_l "
            "(_NL_LOCALE_NAME (category), locale).  */",
            patch,
        )
        self.assertEqual(patch.count("diff --git "), 1)


if __name__ == "__main__":
    unittest.main()
