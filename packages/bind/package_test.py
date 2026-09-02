import os
import unittest
from unittest import mock

from .package import BindPackage


class BindPackageTest(unittest.TestCase):
    @mock.patch("packages.bind.package.steps.run_configure")
    def test_configure_uses_nonthreaded_signal_loop(self, run_configure):
        env = {"PORTS_SYSROOT": "/sysroot"}

        BindPackage(__file__).configure(env, "/source")

        self.assertEqual(env["ac_cv_func_sigwait"], "no")
        self.assertEqual(env["ac_cv_lib_c_sigwait"], "no")
        self.assertEqual(env["ac_cv_lib_pthread_sigwait"], "no")
        self.assertEqual(env["ac_cv_lib_pthread__Psigwait"], "no")
        self.assertEqual(env["ac_cv_lib_c_r_sigwait"], "no")
        run_configure.assert_called_once()
        options = run_configure.call_args.kwargs["extra_config"]
        self.assertIn("--disable-threads", options)
        self.assertNotIn("--enable-threads", options)

    def test_pedigree_truncate_uses_supported_fd_variant(self):
        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "pedigree-truncate.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        pedigree_branch = patch.split("+#ifdef __pedigree__", 1)[1]
        pedigree_branch = pedigree_branch.split("+#else", 1)[0]
        self.assertIn("ftruncate(fd, size)", pedigree_branch)
        self.assertNotIn("\ttruncate(filename, size)", pedigree_branch)


if __name__ == "__main__":
    unittest.main()
