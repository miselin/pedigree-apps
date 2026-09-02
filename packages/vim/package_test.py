import pathlib
import tempfile
import unittest
from unittest import mock

from .package import VimPackage


class VimPackageTest(unittest.TestCase):
    def test_runtime_dependencies_cover_installed_documentation_tools(self):
        self.assertEqual(
            VimPackage(__file__).install_deps(), ["ncurses", "perl"]
        )

    def test_pedigree_timeout_fallback_avoids_sigpending(self):
        package = VimPackage(__file__)

        self.assertEqual(
            package.patches({}, "/source"),
            ["pedigree-no-sigpending.diff"],
        )

        patch_path = pathlib.Path(__file__).parent / "patches" / (
            "pedigree-no-sigpending.diff"
        )
        patch = patch_path.read_text(encoding="utf-8")

        self.assertIn("+#ifdef __pedigree__", patch)
        self.assertIn(
            "+\tret = sigprocmask(SIG_SETMASK, &saved_sigs, NULL);",
            patch,
        )
        self.assertNotIn("+    ret = ret == 0 ? sigpending", patch)

    def test_pedigree_suspend_uses_translated_kill(self):
        patch_path = pathlib.Path(__file__).parent / "patches" / (
            "pedigree-no-sigpending.diff"
        )
        patch = patch_path.read_text(encoding="utf-8")

        self.assertIn("+\tkill(getpid(), sigarg);", patch)
        self.assertNotIn("+\traise(sigarg);", patch)

    @mock.patch("packages.vim.package.steps.run_configure")
    def test_configure_links_split_terminfo_library(self, run_configure):
        VimPackage(__file__).configure({}, "/source")

        self.assertIn(
            "--with-tlib=tinfow",
            run_configure.call_args.kwargs["extra_config"],
        )

    def test_postdeploy_omits_optional_tools_with_unavailable_interpreters(self):
        with tempfile.TemporaryDirectory() as deploydir:
            tools = pathlib.Path(deploydir, "usr/share/vim/vim92/tools")
            tools.mkdir(parents=True)
            (tools / "vim132").write_text("#!/bin/csh\n")

            VimPackage(__file__).postdeploy({}, "/source", deploydir)

            self.assertFalse(tools.exists())


if __name__ == "__main__":
    unittest.main()
