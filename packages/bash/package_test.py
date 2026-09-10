import os
import tempfile
import unittest
from unittest import mock

from .package import BashPackage


class BashPackageTest(unittest.TestCase):
    def test_release_version_has_numeric_pedigree_revision(self):
        package = BashPackage(__file__)

        self.assertEqual(package.version(), "5.3.15")
        self.assertEqual(package.release_version(), "5.3.15.1")

    def test_legacy_absolute_path_patch_is_not_applied(self):
        self.assertNotIn(
            "pedigree-bash.diff",
            BashPackage(__file__).patches({}, "/source"),
        )

    @mock.patch('packages.bash.package.steps.run_configure')
    def test_configure_links_split_terminfo_library(self, run_configure):
        env = {}

        BashPackage(__file__).configure(env, '/source')

        self.assertEqual(env['LIBS'], '-ltinfow')
        self.assertIn(
            '--with-installed-readline',
            run_configure.call_args.kwargs['extra_config'],
        )

    @mock.patch('packages.bash.package.steps.make')
    def test_build_keeps_target_libraries_out_of_host_tools(self, make):
        BashPackage(__file__).build({}, '/source')

        self.assertIn(
            'LIBS_FOR_BUILD=', make.call_args.kwargs['extra_opts'])

    @mock.patch('packages.bash.package.steps.make')
    def test_deploy_keeps_target_libraries_out_of_host_tools(self, make):
        BashPackage(__file__).deploy({}, '/source', '/stage')

        self.assertIn(
            'LIBS_FOR_BUILD=', make.call_args.kwargs['extra_opts'])

    def test_postdeploy_sanitizes_bashbug_build_metadata(self):
        with tempfile.TemporaryDirectory() as deploydir:
            bindir = os.path.join(deploydir, "usr", "bin")
            pkgconfig_dir = os.path.join(
                deploydir, "usr", "lib", "pkgconfig")
            loadable_dir = os.path.join(deploydir, "usr", "lib", "bash")
            os.makedirs(bindir)
            os.makedirs(pkgconfig_dir)
            os.makedirs(loadable_dir)

            env = {
                "APPS_BASE": "/workspace",
                "CROSS_BASE": "/opt/pedigree",
                "CROSS_CC": (
                    "/opt/pedigree/bin/x86_64-pedigree-gcc"
                ),
                "PORTS_SYSROOT": (
                    "/workspace/.build/x86_64/sysroots/bash"
                ),
                "TARGET_SYSROOT": "/opt/pedigree/x86_64-pedigree",
            }
            bashbug = os.path.join(bindir, "bashbug")
            with open(bashbug, "w", encoding="utf-8") as script:
                script.write(
                    '#!/bin/sh\n'
                    'CC="%s"\n'
                    'CFLAGS="-O2 -I%s/usr/include '
                    '-I/usr/include/bash --sysroot=%s '
                    '-Wl,-rpath-link,%s/usr/lib"\n'
                    % (
                        env["CROSS_CC"],
                        env["PORTS_SYSROOT"],
                        env["TARGET_SYSROOT"],
                        env["PORTS_SYSROOT"],
                    )
                )
            os.chmod(bashbug, 0o555)
            bash_pc = os.path.join(pkgconfig_dir, "bash.pc")
            with open(bash_pc, "w", encoding="utf-8") as metadata:
                metadata.write(
                    "CC = %s\nSHOBJ_CC = %s\nCflags: -I/usr/include/bash\n"
                    % (env["CROSS_CC"], env["CROSS_CC"])
                )
            loadable = os.path.join(loadable_dir, "accept")
            with open(loadable, "wb") as module:
                module.write(b"ELF fixture")
            os.chmod(loadable, 0o755)

            BashPackage(__file__).postdeploy(env, "", deploydir)

            with open(bashbug, encoding="utf-8") as script:
                contents = script.read()
            self.assertIn('CC="gcc"', contents)
            self.assertIn("-I/usr/include", contents)
            self.assertIn("-I/usr/include/bash", contents)
            self.assertNotIn("--sysroot", contents)
            self.assertNotIn("rpath-link", contents)
            self.assertNotIn(env["CROSS_BASE"], contents)
            self.assertNotIn(env["PORTS_SYSROOT"], contents)
            self.assertEqual(os.stat(bashbug).st_mode & 0o777, 0o555)

            with open(bash_pc, encoding="utf-8") as metadata:
                pc_contents = metadata.read()
            self.assertIn("CC = gcc", pc_contents)
            self.assertIn("SHOBJ_CC = gcc", pc_contents)
            self.assertNotIn(env["CROSS_BASE"], pc_contents)
            self.assertEqual(os.stat(loadable).st_mode & 0o777, 0o644)


if __name__ == "__main__":
    unittest.main()
