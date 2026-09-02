import pathlib
import unittest
from unittest import mock

from .package import InetutilsPackage, MAKE_OPTIONS


class InetutilsPackageTest(unittest.TestCase):
    def test_build_keeps_distributed_man_pages_in_cross_build(self):
        self.assertEqual(MAKE_OPTIONS, ("HELP2MAN=true",))

    def test_inetd_uses_pause_when_sigsuspend_is_unavailable(self):
        package = InetutilsPackage(__file__)

        self.assertEqual(
            package.patches({}, "/source"),
            ["pselect-null.diff", "pedigree-inetd-pause.diff"],
        )

        patch_path = pathlib.Path(__file__).parent / "patches" / (
            "pedigree-inetd-pause.diff"
        )
        patch = patch_path.read_text(encoding="utf-8")

        self.assertIn("+# if defined HAVE_SIGSUSPEND", patch)
        self.assertIn("+# define inetd_pause(s) pause()", patch)

    @mock.patch("packages.inetutils.package.steps.run_configure")
    def test_configure_disables_staged_dependency_rpaths(self, run_configure):
        InetutilsPackage(__file__).configure({}, "/source")

        self.assertIn(
            "--disable-rpath",
            run_configure.call_args.kwargs["extra_config"],
        )


if __name__ == "__main__":
    unittest.main()
