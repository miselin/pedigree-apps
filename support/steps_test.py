import hashlib
import io
import os
import tempfile
import unittest
from unittest import mock

from . import steps


class StepsTest(unittest.TestCase):
    def setUp(self):
        self.command = mock.MagicMock()
        self.original_command = steps.cmd
        steps.cmd = self.command

    def tearDown(self):
        steps.cmd = self.original_command

    def test_get_builddir(self):
        with mock.patch("support.steps.os.makedirs") as makedirs:
            self.assertEqual(steps.get_builddir("s", {}, True), "s")
            self.assertEqual(steps.get_builddir("s", {}, False), "s/pedigree-build")
            makedirs.assert_called_once_with("s/pedigree-build", exist_ok=True)

    def test_libtoolize_uses_host_build_tool(self):
        env = {"LIBTOOLIZE": "/usr/bin/libtoolize"}
        steps.libtoolize(".", env)
        self.command.assert_called_with(
            [
                "/usr/bin/libtoolize",
                "--install",
                "--verbose",
                "--force",
                "--ltdl",
            ],
            cwd=".",
            env=env,
        )

    def test_fhs_configure_paths(self):
        self.assertEqual(steps.AUTOCONF_PATHFLAGS["prefix"], "/usr")
        self.assertEqual(steps.AUTOCONF_PATHFLAGS["libdir"], "/usr/lib")
        self.assertEqual(steps.AUTOCONF_PATHFLAGS["sysconfdir"], "/etc")

    def test_serial_make_overrides_environment_parallelism(self):
        env = {"MAKE": "/usr/bin/make", "MAKEFLAGS": "-j8"}
        steps.make(".", env, parallel=False)
        command_env = self.command.call_args.kwargs["env"]
        self.assertEqual(command_env["MAKEFLAGS"], "-j1")
        self.assertEqual(self.command.call_args.args[0], ["/usr/bin/make"])

    def test_upload_command_redacts_keys(self):
        self.assertEqual(
            steps._redacted_command(["pup", "--key", "secret"]),
            ["pup", "--key", "<redacted>"],
        )

    def test_upload_key_is_passed_outside_command_line(self):
        package = mock.Mock()
        package.name.return_value = "example"
        package.version.return_value = "1.0"
        package.install_deps.return_value = []
        env = {
            "PACKMAN_SCRIPT": "/usr/bin/pup",
            "PACKMAN_CONFIG": "/tmp/pup.conf",
            "PACKMAN_REPO": "/tmp",
            "BUILD_BASE": "/tmp",
            "PACKMAN_TARGET_ARCH": "amd64",
            "UPLOAD_KEY": "must-not-be-inherited",
        }
        steps.pup_package(
            package,
            "/tmp/root",
            env,
            upload=True,
            upload_key="secret",
        )
        command = self.command.call_args.args[0]
        command_env = self.command.call_args.kwargs["env"]
        self.assertNotIn("secret", command)
        self.assertNotIn("UPLOAD_KEY", command_env)
        self.assertEqual(command_env["PUP_UPLOAD_KEY"], "secret")

    def test_rejected_upload_removes_temporary_config(self):
        package = mock.Mock()
        package.name.return_value = "dependent"
        package.version.return_value = "1.0"
        package.install_deps.return_value = ["runtime"]
        with tempfile.TemporaryDirectory() as temporary:
            env = {
                "PACKMAN_SCRIPT": "/usr/bin/pup",
                "PACKMAN_CONFIG": os.path.join(temporary, "pup.conf"),
                "PACKMAN_REPO": os.path.join(temporary, "repo"),
                "PACKMAN_TARGET_ARCH": "amd64",
                "BUILD_BASE": temporary,
            }
            with self.assertRaisesRegex(RuntimeError, "runtime dependencies"):
                steps.pup_package(
                    package,
                    "/tmp/root",
                    env,
                    upload=True,
                    upload_key="secret",
                )
            self.assertEqual(
                [name for name in os.listdir(temporary) if name.startswith("pup-")],
                [],
            )

    def test_download_verifies_cached_file(self):
        content = b"verified source"
        with tempfile.TemporaryDirectory() as temporary:
            target = os.path.join(temporary, "source.tar")
            with open(target, "wb") as source:
                source.write(content)
            with mock.patch("support.steps.urllib.request.urlopen") as urlopen:
                steps.download(
                    "https://example.invalid/source.tar",
                    target,
                    sha256=hashlib.sha256(content).hexdigest(),
                )
            urlopen.assert_not_called()

    def test_download_replaces_bad_cached_file(self):
        content = b"replacement source"
        with tempfile.TemporaryDirectory() as temporary:
            target = os.path.join(temporary, "source.tar")
            with open(target, "wb") as source:
                source.write(b"bad cache")
            with mock.patch(
                "support.steps.urllib.request.urlopen",
                return_value=io.BytesIO(content),
            ):
                steps.download(
                    "https://example.invalid/source.tar",
                    target,
                    sha256=hashlib.sha256(content).hexdigest(),
                )
            with open(target, "rb") as source:
                self.assertEqual(source.read(), content)


if __name__ == "__main__":
    unittest.main()
