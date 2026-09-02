import unittest
from unittest import mock

from .package import LynxPackage


class LynxPackageTest(unittest.TestCase):
    @mock.patch("packages.lynx.package.steps.run_configure")
    def test_configure_omits_unsupported_docdir(self, run_configure):
        LynxPackage(__file__).configure({}, "/source")

        self.assertEqual(
            run_configure.call_args.kwargs["not_paths"], ("docdir",)
        )
        self.assertIn(
            "--with-screen=ncursesw",
            run_configure.call_args.kwargs["extra_config"],
        )

    @mock.patch("packages.lynx.package.steps.run_configure")
    def test_configure_keeps_dired_without_external_archivers(
        self, run_configure
    ):
        LynxPackage(__file__).configure({}, "/source")

        extra_config = run_configure.call_args.kwargs["extra_config"]
        self.assertNotIn("--disable-dired", extra_config)
        for option in (
            "--disable-dired-dearchive",
            "--disable-dired-gzip",
            "--disable-dired-tar",
            "--disable-dired-uudecode",
            "--disable-dired-zip",
        ):
            self.assertIn(option, extra_config)

    @mock.patch("packages.lynx.package.steps.make")
    def test_recursive_builds_run_serially(self, make):
        package = LynxPackage(__file__)

        package.build({}, "/source")
        self.assertFalse(make.call_args.kwargs["parallel"])

        package.deploy({}, "/source", "/stage")
        self.assertFalse(make.call_args.kwargs["parallel"])
        self.assertIn(
            "DESTDIR=/stage", make.call_args.kwargs["extra_opts"]
        )


if __name__ == "__main__":
    unittest.main()
