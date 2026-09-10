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
