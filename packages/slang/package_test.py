import os
import unittest
from unittest import mock

from .package import SlangPackage


class SlangPackageTest(unittest.TestCase):

    def setUp(self):
        self.package = SlangPackage(__file__)

    def test_runtime_contract_uses_ncurses_terminfo(self):
        self.assertEqual(self.package.build_requires(), ["ncurses"])
        self.assertEqual(self.package.install_deps(), ["ncurses"])
        self.assertEqual(
            self.package.patches({}, "/source"), ["pedigree-target.diff"]
        )

    @mock.patch("packages.slang.package.steps.run_configure")
    def test_configure_avoids_host_tools_and_stubbed_signals(
        self, run_configure
    ):
        env = {"TARGET_CONFIG_SITE": "/workspace/config.site"}

        self.package.configure(env, "/source")

        for function in (
            "cfgetospeed",
            "getitimer",
            "issetugid",
            "mkfifo",
            "pathconf",
            "pause",
            "setitimer",
            "sigsuspend",
            "socketpair",
        ):
            with self.subTest(function=function):
                self.assertEqual(env["ac_cv_func_%s" % function], "no")
        self.assertEqual(env["ac_cv_func_isinf"], "yes")
        self.assertEqual(env["ac_cv_func_isnan"], "yes")
        self.assertEqual(env["ac_cv_path_nc5config"], "no")
        options = run_configure.call_args.kwargs["extra_config"]
        self.assertIn("--with-readline=slang", options)
        self.assertIn("--with-terminfo=default", options)
        for option in (
            "--without-iconv",
            "--without-onig",
            "--without-pcre",
            "--without-png",
            "--without-x",
            "--without-z",
        ):
            with self.subTest(option=option):
                self.assertIn(option, options)

    def test_patch_selects_elf_terminfo_and_safe_signal_fallback(self):
        patch_path = os.path.join(
            os.path.dirname(__file__), "patches", "pedigree-target.diff"
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn("*pedigree*", patch)
        self.assertIn(
            '+    MISC_TERMINFO_DIRS="/usr/share/terminfo"', patch
        )
        self.assertIn("SL_NotImplemented_Error", patch)
        self.assertIn("!defined(__PEDIGREE__)", patch)
        self.assertIn("defined(__PEDIGREE__)", patch)
        self.assertNotIn(
            '+   MAKE_INTRINSIC_0("setsockopt", setsockopt_intrin, V),',
            patch,
        )


if __name__ == "__main__":
    unittest.main()
