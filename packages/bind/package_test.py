import os
import unittest
from unittest import mock

from .package import BindPackage


class BindPackageTest(unittest.TestCase):
    @mock.patch("packages.bind.package.steps.run_configure")
    def test_configure_uses_nonthreaded_signal_loop(self, run_configure):
        env = {"PORTS_SYSROOT": "/sysroot"}

        BindPackage(__file__).configure(env, "/source")

        self.assertNotIn("ac_cv_func_sigwait", env)
        run_configure.assert_called_once()
        options = run_configure.call_args.kwargs["extra_config"]
        self.assertIn("--disable-threads", options)
        self.assertNotIn("--enable-threads", options)


if __name__ == "__main__":
    unittest.main()
