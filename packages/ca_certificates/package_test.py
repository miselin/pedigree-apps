import os
import stat
import tempfile
import unittest
from unittest import mock

from .package import CaCertificatesPackage


class CaCertificatesPackageTest(unittest.TestCase):
    def test_source_is_immutable_and_pinned(self):
        package = CaCertificatesPackage(__file__)

        with mock.patch(
            "packages.ca_certificates.package.steps.download"
        ) as download:
            package.download({}, "/download")

        download.assert_called_once_with(
            "https://curl.se/ca/cacert-2026-08-13.pem",
            "/download",
            sha256=(
                "f66dff1bdf8f96060b8177976f8b7d92"
                "54bc89bc4db933d769f7384d28480bc9"
            ),
        )
        self.assertEqual(package.version(), "2026.08.13")
        self.assertEqual(package.options().tarfile_format, "bare")

    def test_deploy_installs_fhs_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            srcdir = os.path.join(temporary, "source")
            deploydir = os.path.join(temporary, "root")
            os.makedirs(srcdir)
            os.makedirs(deploydir)
            with open(os.path.join(srcdir, "source"), "wb") as source:
                source.write(
                    b"-----BEGIN CERTIFICATE-----\n"
                    b"fixture\n"
                    b"-----END CERTIFICATE-----\n"
                )

            package = CaCertificatesPackage(__file__)
            package.deploy({}, srcdir, deploydir)
            package.postdeploy({}, srcdir, deploydir)

            bundle = os.path.join(deploydir, "etc", "ssl", "cert.pem")
            self.assertTrue(os.path.isfile(bundle))
            self.assertEqual(stat.S_IMODE(os.stat(bundle).st_mode), 0o644)

    def test_postdeploy_rejects_private_keys(self):
        with tempfile.TemporaryDirectory() as deploydir:
            ssl_dir = os.path.join(deploydir, "etc", "ssl")
            os.makedirs(ssl_dir)
            with open(os.path.join(ssl_dir, "cert.pem"), "wb") as bundle:
                bundle.write(
                    b"-----BEGIN CERTIFICATE-----\n"
                    b"fixture\n"
                    b"-----END CERTIFICATE-----\n"
                    b"-----BEGIN PRIVATE KEY-----\n"
                )

            with self.assertRaisesRegex(RuntimeError, "private key"):
                CaCertificatesPackage(__file__).postdeploy(
                    {}, "", deploydir
                )


if __name__ == "__main__":
    unittest.main()
