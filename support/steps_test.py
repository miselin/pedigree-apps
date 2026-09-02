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

    def test_configure_scopes_target_config_site(self):
        package = mock.Mock()
        package.name.return_value = "example"
        env = {
            "CROSS_TARGET": "x86_64-pedigree",
            "TARGET_CONFIG_SITE": "/workspace/config.site",
        }

        steps.run_configure(package, "/source", env)

        command_env = self.command.call_args.kwargs["env"]
        self.assertEqual(command_env["CONFIG_SITE"], "/workspace/config.site")
        self.assertNotIn("CONFIG_SITE", env)

    def test_configure_scopes_libtool_dependencies_to_ports_sysroot(self):
        package = mock.Mock()
        package.name.return_value = "example"
        with tempfile.TemporaryDirectory() as source:
            configure = os.path.join(source, "configure")
            with open(configure, "w", encoding="utf-8") as script:
                script.write("# supports --with-sysroot for libtool\n")
            env = {
                "CROSS_TARGET": "x86_64-pedigree",
                "PORTS_SYSROOT": "/workspace/.build/sysroots/example",
                "TARGET_CONFIG_SITE": "/workspace/config.site",
            }

            steps.run_configure(package, source, env)

        command = self.command.call_args.args[0]
        self.assertIn(
            "--with-sysroot=/workspace/.build/sysroots/example", command
        )

    def test_libtool_configure_adds_only_pedigree_elf_cases(self):
        with tempfile.TemporaryDirectory() as source:
            nested = os.path.join(source, "extension")
            os.makedirs(nested)
            configure = os.path.join(nested, "configure")
            with open(configure, "w", encoding="utf-8") as script:
                script.write(
                    "lt_cv_deplibs_check_method=unknown\n"
                    "lt_prog_compiler_wl=\n"
                    "case $host_os in\n"
                    "  linux* | k*bsd*-gnu | gnu*)\n"
                    "    version_type=linux ;;\n"
                    "  s390*-*linux*|s390*-*tpf*) s390_linker=yes ;;\n"
                    "  linux*) use_epoll=yes ;;\n"
                    "esac\n"
                )

            steps.patch_libtool_configure(source)
            steps.patch_libtool_configure(source)

            with open(configure, encoding="utf-8") as script:
                contents = script.read()

        self.assertIn("linux* | pedigree* | k*bsd*-gnu | gnu*)", contents)
        self.assertEqual(contents.count("pedigree*"), 1)
        self.assertIn("s390*-*linux*|s390*-*tpf*)", contents)
        self.assertIn("linux*) use_epoll=yes ;;", contents)

    def test_meson_cross_file_uses_pedigree_and_staged_flags(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = os.path.join(temporary, "source")
            os.makedirs(source)
            env = {
                "MESON": "/opt/meson",
                "CCACHE": "/usr/bin/ccache",
                "CROSS_CC": "/opt/x86_64-pedigree-gcc",
                "CROSS_CXX": "/opt/x86_64-pedigree-g++",
                "CROSS_AR": "/opt/x86_64-pedigree-ar",
                "CROSS_STRIP": "/opt/x86_64-pedigree-strip",
                "PKG_CONFIG": "/usr/bin/pkg-config",
                "TARGET_SYSROOT": "/opt/pedigree/x86_64-pedigree",
                "CFLAGS": "-O2",
                "CXXFLAGS": "-O2",
                "CPPFLAGS": "-I/staged/usr/include",
                "LDFLAGS": "-L/staged/usr/lib",
            }

            steps.meson_configure(mock.Mock(), source, env)
            cross_file = os.path.join(
                source, "pedigree-build", "pedigree-cross.ini"
            )
            with open(cross_file, encoding="utf-8") as config:
                contents = config.read()

        self.assertIn("system = 'pedigree'", contents)
        self.assertIn("needs_exe_wrapper = true", contents)
        self.assertIn("'-I/staged/usr/include'", contents)
        self.assertNotIn("sys_root", contents)
        self.assertNotIn("system = 'linux'", contents)

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
