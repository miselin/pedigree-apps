import pathlib
import tempfile
import unittest
from unittest import mock

from .package import GitPackage, MAKE_OPTIONS


class GitPackageTest(unittest.TestCase):
    @mock.patch("packages.git.package.steps.run_configure")
    def test_configure_answers_iconv_cross_runtime_probe(self, run_configure):
        GitPackage(__file__).configure({}, "/source")

        self.assertIn(
            "ac_cv_iconv_omits_bom=no",
            run_configure.call_args.kwargs["extra_config"],
        )

    def test_build_omits_rust(self):
        self.assertIn("NO_RUST=YesPlease", MAKE_OPTIONS)

    def test_build_disables_linux_fsmonitor_backend(self):
        self.assertIn("FSMONITOR_DAEMON_BACKEND=", MAKE_OPTIONS)
        self.assertIn("FSMONITOR_OS_SETTINGS=", MAKE_OPTIONS)

    @mock.patch("packages.git.package.steps.make")
    def test_build_uses_staged_curl_config(self, make):
        GitPackage(__file__).build(
            {"PORTS_SYSROOT": "/ports-sysroot"}, "/source"
        )

        self.assertIn(
            "CURL_CONFIG=/ports-sysroot/usr/bin/curl-config",
            make.call_args.kwargs["extra_opts"],
        )

    def test_postdeploy_omits_perl_watchman_sample(self):
        with tempfile.TemporaryDirectory() as deploydir:
            sample = pathlib.Path(
                deploydir,
                "usr/share/git-core/templates/hooks/fsmonitor-watchman.sample",
            )
            sample.parent.mkdir(parents=True)
            sample.write_text("#!/usr/bin/perl\n")

            GitPackage(__file__).postdeploy({}, "/source", deploydir)

            self.assertFalse(sample.exists())


if __name__ == "__main__":
    unittest.main()
