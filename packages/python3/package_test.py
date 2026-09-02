import json
import os
import tempfile
import unittest
from unittest import mock

from .package import Python3Package


class Python3PackageTest(unittest.TestCase):
    def test_config_site_disables_untranslated_python_syscalls(self):
        config_site = os.path.join(
            os.path.dirname(__file__), "..", "..", "config.site"
        )
        with open(config_site, encoding="utf-8") as config_file:
            answers = set(config_file.read().splitlines())

        self.assertTrue(
            {
                "ac_cv_func_fexecve=no",
                "ac_cv_func_lchmod=no",
                "ac_cv_func_lutimes=no",
                "ac_cv_func_mkfifoat=no",
                "ac_cv_func_mknodat=no",
                "ac_cv_func_pthread_getattr_np=no",
                "ac_cv_func_pthread_kill=no",
                "ac_cv_func_sigpending=no",
                "ac_cv_func_sigtimedwait=no",
                "ac_cv_func_sigwait=no",
                "ac_cv_func_sigwaitinfo=no",
                "ac_cv_func_truncate=no",
            }.issubset(answers)
        )

    @mock.patch("packages.python3.package.steps.cmd")
    def test_prebuild_uses_case_distinct_host_python(self, cmd):
        with tempfile.TemporaryDirectory() as srcdir:
            env = {"MAKE": "make", "MAKEFLAGS": "-j8"}
            package = Python3Package(__file__)

            package.prebuild(env, srcdir)

            self.assertEqual(
                package._host_python(srcdir),
                os.path.join(srcdir, "pedigree-host-build", "python-host"),
            )
            self.assertEqual(
                cmd.call_args_list[1].args[0],
                [
                    "make",
                    "-j8",
                    "BUILDPYTHON=python-host",
                    "python-host",
                ],
            )

    @mock.patch("packages.python3.package.steps.run_configure")
    @mock.patch(
        "packages.python3.package.steps.cmd_output",
        return_value="x86_64-unknown-linux-gnu\n",
    )
    def test_configure_sets_cross_runtime_answers(
        self, cmd_output, run_configure
    ):
        env = {"CPPFLAGS": "-I/staged/usr/include"}
        package = Python3Package(__file__)

        package.configure(env, "/source")

        self.assertEqual(env["ac_cv_aligned_required"], "no")
        self.assertEqual(env["ac_cv_file__dev_ptc"], "no")
        self.assertEqual(env["ac_cv_file__dev_ptmx"], "yes")
        self.assertEqual(env["ac_cv_func_pthread_getcpuclockid"], "no")
        self.assertEqual(
            env["LIBREADLINE_CFLAGS"], "-I/staged/usr/include"
        )
        self.assertEqual(
            env["LIBREADLINE_LIBS"],
            "-lreadline -lncursesw -ltinfow",
        )
        cmd_output.assert_called_once()
        extra_config = run_configure.call_args.kwargs["extra_config"]
        self.assertIn("--disable-ipv6", extra_config)
        self.assertIn("--without-mimalloc", extra_config)

    def test_postdeploy_sanitizes_cross_build_metadata(self):
        with tempfile.TemporaryDirectory() as deploydir:
            bindir = os.path.join(deploydir, "usr", "bin")
            python_dir = os.path.join(deploydir, "usr", "lib", "python3.14")
            config_dir = os.path.join(
                python_dir, "config-3.14-x86_64-pedigree"
            )
            os.makedirs(bindir)
            os.makedirs(config_dir)

            cross_base = "/opt/pedigree/bin/x86_64-pedigree-"
            srcdir = (
                "/workspace/.build/x86_64/work/python3-3.14.7/src"
            )
            builddir = srcdir + "/pedigree-build"
            host_python = srcdir + "/pedigree-host-build/python-host"
            ports_sysroot = "/workspace/.build/amd64/sysroots/python3"
            staged_include = ports_sysroot + "/usr/include"
            staged_lib = ports_sysroot + "/usr/lib"
            metadata = {
                "CC": cross_base + "gcc",
                "CXX": cross_base + "g++",
                "AR": cross_base + "ar",
                "CPPFLAGS": (
                    "-I%s -I%s/ncursesw -I%s/Include/internal "
                    "-I/usr/include/python3.14"
                    % (staged_include, staged_include, srcdir)
                ),
                "LDFLAGS": (
                    "-L%s -Wl,-rpath-link,%s -L/usr/lib"
                    % (staged_lib, staged_lib)
                ),
                "PKG_CONFIG_LIBDIR": (
                    ports_sysroot
                    + "/usr/lib/pkgconfig:"
                    + ports_sysroot
                    + "/usr/share/pkgconfig"
                ),
                "abs_srcdir": srcdir,
                "abs_builddir": builddir,
                "PYTHON_FOR_BUILD": (
                    "_PYTHON_PROJECT_BASE=%s %s" % (builddir, host_python)
                ),
                "userbase": "/tmp/.local",
            }
            json_path = os.path.join(
                python_dir,
                "_sysconfig_vars__pedigree_x86_64-pedigree.json",
            )
            with open(json_path, "w", encoding="utf-8") as metadata_file:
                json.dump(metadata, metadata_file)

            python_path = os.path.join(
                python_dir,
                "_sysconfigdata__pedigree_x86_64-pedigree.py",
            )
            with open(python_path, "w", encoding="utf-8") as metadata_file:
                metadata_file.write("build_time_vars = %r\n" % metadata)

            details_path = os.path.join(python_dir, "build-details.json")
            with open(details_path, "w", encoding="utf-8") as metadata_file:
                json.dump({"build": metadata}, metadata_file)

            makefile_path = os.path.join(config_dir, "Makefile")
            with open(makefile_path, "w", encoding="utf-8") as metadata_file:
                metadata_file.write(
                    "CC=%s\nCPPFLAGS=%s\nLDFLAGS=%s\n"
                    % (
                        cross_base + "gcc",
                        metadata["CPPFLAGS"],
                        metadata["LDFLAGS"],
                    )
                )

            env = {
                "APPS_BASE": "/workspace",
                "BUILD_BASE": "/workspace/.build/x86_64",
                "CROSS_BASE": "/opt/pedigree",
                "CROSS_AR": cross_base + "ar",
                "CROSS_AS": cross_base + "as",
                "CROSS_CC": cross_base + "gcc",
                "CROSS_CPP": cross_base + "cpp",
                "CROSS_CXX": cross_base + "g++",
                "CROSS_LD": cross_base + "ld",
                "CROSS_RANLIB": cross_base + "ranlib",
                "CROSS_STRIP": cross_base + "strip",
                "PORTS_SYSROOT": ports_sysroot,
                "HOME": "/tmp",
            }
            package = Python3Package(__file__)
            package.postdeploy(env, srcdir, deploydir)

            self.assertEqual(
                os.readlink(os.path.join(bindir, "python")), "python3"
            )
            for path in (
                json_path,
                python_path,
                details_path,
                makefile_path,
            ):
                with open(path, encoding="utf-8") as metadata_file:
                    contents = metadata_file.read()
                self.assertNotIn("/opt/pedigree", contents)
                self.assertNotIn("/workspace", contents)
                self.assertNotIn(ports_sysroot, contents)
                self.assertNotIn("-I%s" % staged_include, contents)
                self.assertNotIn("-L%s" % staged_lib, contents)
                self.assertNotIn(
                    "-Wl,-rpath-link,%s" % staged_lib, contents
                )
                self.assertNotIn("/tmp/.local", contents)
                self.assertIn("-I/usr/include/python3.14", contents)
                self.assertIn("-L/usr/lib", contents)

            with open(json_path, encoding="utf-8") as metadata_file:
                sanitized = json.load(metadata_file)
            self.assertEqual(sanitized["CC"], "gcc")
            self.assertEqual(sanitized["CXX"], "g++")
            self.assertEqual(sanitized["AR"], "ar")
            self.assertEqual(sanitized["userbase"], "")
            self.assertEqual(
                sanitized["abs_srcdir"],
                "/usr/lib/python3.14/config-3.14-x86_64-pedigree",
            )
            self.assertEqual(
                sanitized["abs_builddir"],
                "/usr/lib/python3.14/config-3.14-x86_64-pedigree",
            )
            self.assertEqual(
                sanitized["PYTHON_FOR_BUILD"],
                "_PYTHON_PROJECT_BASE=/usr/lib/python3.14/"
                "config-3.14-x86_64-pedigree python3",
            )
            self.assertIn(
                "-I/usr/include/python3.14/internal",
                sanitized["CPPFLAGS"],
            )
            self.assertIn("-I/usr/include/ncursesw", sanitized["CPPFLAGS"])
            self.assertEqual(
                sanitized["PKG_CONFIG_LIBDIR"],
                "/usr/lib/pkgconfig:/usr/share/pkgconfig",
            )


if __name__ == "__main__":
    unittest.main()
