import os
import tempfile
import unittest
from unittest import mock

from .package import PerlPackage


class PerlPackageTest(unittest.TestCase):
    def test_release_version_has_numeric_pedigree_revision(self):
        package = PerlPackage(__file__)

        self.assertEqual(package.version(), "5.44.0")
        self.assertEqual(package.release_version(), "5.44.0.1")

    def test_errno_patch_uses_target_os_and_toolchain_sysroot(self):
        patch_path = os.path.join(
            os.path.dirname(__file__), "patches", "errno-cross.diff"
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn("$Config{osname} eq 'pedigree'", patch)
        self.assertIn('"$sysroot/include"', patch)
        self.assertNotIn("$^O eq 'pedigree'", patch)

    def test_bootstrap_write_patch_is_cross_build_only(self):
        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "bootstrap-writable-dir.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn("$^O eq 'linux'", patch)
        self.assertIn("$Config{osname} eq 'pedigree'", patch)
        self.assertIn("-d $dir", patch)

    def test_pedigree_path_truncate_uses_ftruncate_fallback(self):
        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "pedigree-truncate.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn(
            "defined(HAS_TRUNCATE) && !defined(__pedigree__)", patch
        )
        self.assertIn("int mode = O_WRONLY", patch)

    def test_pedigree_redirects_signals_to_the_primary_thread(self):
        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "pedigree-thread-signal.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        pedigree_branch = patch.split("+#ifdef __pedigree__", 1)[1]
        pedigree_branch = pedigree_branch.split("+#else", 1)[0]
        self.assertIn("kill(getpid(), sig)", pedigree_branch)
        self.assertNotIn("pthread_kill", pedigree_branch)

    def test_extension_probes_respect_missing_pedigree_syscalls(self):
        package_dir = os.path.dirname(__file__)
        patch_path = os.path.join(
            package_dir,
            "patches",
            "pedigree-missing-syscalls.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()
        with open(
            os.path.join(package_dir, "pedigree.hint"), encoding="utf-8"
        ) as hint_file:
            hint = hint_file.read()

        self.assertIn("defined(__pedigree__)", patch)
        self.assertIn("$Config{d_futimens}", patch)
        self.assertIn("$Config{d_utimensat}", patch)
        self.assertIn("d_futimens='undef'", hint)
        self.assertIn("d_utimensat='undef'", hint)

    @mock.patch("packages.perl.package.steps.cmd")
    @mock.patch(
        "packages.perl.package.steps.cmd_output",
        return_value="x86_64-pc-linux-gnu\n",
    )
    @mock.patch(
        "packages.perl.package.shutil.which",
        side_effect=lambda tool: "/usr/bin/%s" % tool,
    )
    def test_configure_matches_perl_cross_feature_profile(
        self, which, cmd_output, cmd
    ):
        env = {
            "CROSS_BASE": "/opt/pedigree",
            "CROSS_TARGET": "x86_64-pedigree",
            "TARGET_SYSROOT": "/opt/pedigree/x86_64-pedigree",
        }
        package = PerlPackage(__file__)

        package.configure(env, "/source")

        configure = cmd.call_args.args[0]
        self.assertIn("-Accflags=-D_GNU_SOURCE", configure)

    def test_postdeploy_sanitizes_installed_development_metadata(self):
        with tempfile.TemporaryDirectory() as deploydir:
            env = {
                "APPS_BASE": "/workspace",
                "CROSS_BASE": "/opt/pedigree",
                "CROSS_TARGET": "x86_64-pedigree",
                "TARGET_SYSROOT": "/opt/pedigree/x86_64-pedigree",
                "PORTS_SYSROOT": (
                    "/workspace/.build/x86_64/sysroots/perl"
                ),
            }
            archlib = os.path.join(
                deploydir,
                "usr",
                "lib",
                "perl5",
                "5.44.0",
                env["CROSS_TARGET"],
            )
            core = os.path.join(archlib, "CORE")
            os.makedirs(core)
            tool_prefix = "/opt/pedigree/bin/x86_64-pedigree-"
            target_sysroot = env["TARGET_SYSROOT"]
            ports_sysroot = env["PORTS_SYSROOT"]
            paths = {
                "Config.pm": "cc => '%sgcc',\n" % tool_prefix,
                "Config_heavy.pl": (
                    "cc='%sgcc'\n"
                    "ar='%sar'\n"
                    "ccflags='--sysroot=%s -D_GNU_SOURCE -O2'\n"
                    "ldflags='--sysroot=%s -L%s/usr/lib "
                    "-Wl,-rpath-link,%s/usr/lib'\n"
                    "config_args='--mode=cross "
                    "--target-tools-prefix=%s --sysroot=%s'\n"
                    "sysroot='%s'\n"
                    % (
                        tool_prefix,
                        tool_prefix,
                        target_sysroot,
                        target_sysroot,
                        ports_sysroot,
                        ports_sysroot,
                        tool_prefix,
                        target_sysroot,
                        target_sysroot,
                    )
                ),
                os.path.join("CORE", "config.h"): (
                    '#define CPPSTDIN "%sgcc -E -P"\n' % tool_prefix
                ),
            }
            for relative, contents in paths.items():
                metadata_path = os.path.join(archlib, relative)
                with open(
                    metadata_path,
                    "w",
                    encoding="utf-8",
                ) as metadata:
                    metadata.write(contents)
                os.chmod(metadata_path, 0o444)

            package = PerlPackage(__file__)
            package.postdeploy(env, "", deploydir)

            combined = ""
            for relative in paths:
                with open(
                    os.path.join(archlib, relative), encoding="utf-8"
                ) as metadata:
                    combined += metadata.read()
                self.assertEqual(
                    os.stat(os.path.join(archlib, relative)).st_mode & 0o777,
                    0o444,
                )
            self.assertNotIn("/workspace", combined)
            self.assertNotIn("/opt/pedigree", combined)
            self.assertNotIn("--sysroot=", combined)
            self.assertNotIn("--target-tools-prefix=", combined)
            self.assertIn("cc='gcc'", combined)
            self.assertIn("ar='ar'", combined)
            self.assertIn("-D_GNU_SOURCE", combined)
            self.assertIn("-L/usr/lib", combined)
            self.assertIn("-Wl,-rpath-link,/usr/lib", combined)
            self.assertIn('#define CPPSTDIN "gcc -E -P"', combined)

    def test_postdeploy_requires_all_development_metadata(self):
        with tempfile.TemporaryDirectory() as deploydir:
            env = {
                "CROSS_BASE": "/opt/pedigree",
                "CROSS_TARGET": "x86_64-pedigree",
                "TARGET_SYSROOT": "/opt/pedigree/x86_64-pedigree",
                "PORTS_SYSROOT": "/workspace/sysroot",
            }
            with self.assertRaisesRegex(
                RuntimeError, "development metadata was not installed"
            ):
                PerlPackage(__file__).postdeploy(env, "", deploydir)


if __name__ == "__main__":
    unittest.main()
