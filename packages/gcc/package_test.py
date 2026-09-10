import hashlib
import os
import tempfile
import unittest
from unittest import mock

from .package import (
    MAINLINE_PATCH_SHA256,
    SOURCE_VERSION,
    TOOLCHAIN_RECIPE,
    GccPackage,
)


class GccPackageTest(unittest.TestCase):

    def setUp(self):
        self.package = GccPackage(__file__)
        self.env = {
            "CROSS_AR": "/opt/pedigree/bin/x86_64-pedigree-ar",
            "CROSS_AS": "/opt/pedigree/bin/x86_64-pedigree-as",
            "CROSS_BASE": "/opt/pedigree",
            "CROSS_CC": "/opt/pedigree/bin/x86_64-pedigree-gcc",
            "CROSS_CFLAGS": "-O2 -m64 -D__PEDIGREE__ -std=gnu17",
            "CROSS_CXX": "/opt/pedigree/bin/x86_64-pedigree-g++",
            "CROSS_CXXFLAGS": "-O2 -m64 -D__PEDIGREE__",
            "CROSS_LD": "/opt/pedigree/bin/x86_64-pedigree-ld",
            "CROSS_RANLIB": "/opt/pedigree/bin/x86_64-pedigree-ranlib",
            "CROSS_TARGET": "x86_64-pedigree",
            "APPS_BASE": "/workspace",
            "LDFLAGS": (
                "-Wl,-z,max-page-size=4096 "
                "-L/workspace/.build/x86_64/sysroots/gcc/usr/lib"
            ),
            "MAKE": "/usr/bin/make",
            "MAKEFLAGS": "-j8",
            "PORTS_SYSROOT": "/workspace/.build/x86_64/sysroots/gcc",
            "TARGET_CONFIG_SITE": "/workspace/config.site",
        }

    def test_matches_mainline_r2_manifest_and_patch(self):
        self.assertEqual(self.package.version(), "15.3.0")
        self.assertEqual(self.package.release_version(), "15.3.0.1")
        self.assertEqual(SOURCE_VERSION, "15.3.0")
        self.assertEqual(TOOLCHAIN_RECIPE, 2)
        patch_path = os.path.join(
            os.path.dirname(__file__), "patches", "pedigree-gcc.diff"
        )
        with open(patch_path, "rb") as patch_file:
            digest = hashlib.sha256(patch_file.read()).hexdigest()
        self.assertEqual(digest, MAINLINE_PATCH_SHA256)

    @mock.patch("packages.gcc.package.steps.download")
    def test_download_is_digest_pinned(self, download):
        self.package.download({}, "/download")

        args = download.call_args.args
        self.assertEqual(
            args[0],
            "https://ftp.gnu.org/gnu/gcc/gcc-15.3.0/"
            "gcc-15.3.0.tar.xz",
        )
        self.assertEqual(
            download.call_args.kwargs["sha256"],
            "fa59c1beef8995f27c4d71c1df227587189315d3e6faff1bb4306e61b0c530eb",
        )

    @mock.patch("packages.gcc.package.steps.patch_libtool_configure")
    def test_prebuild_enables_pedigree_shared_lto_plugin(self, patch_libtool):
        self.package.prebuild(self.env, "/source")

        patch_libtool.assert_called_once_with("/source")

    @mock.patch("packages.gcc.package.steps.cmd")
    @mock.patch(
        "packages.gcc.package.steps.cmd_output",
        return_value="x86_64-pc-linux-gnu\n",
    )
    @mock.patch(
        "packages.gcc.package.shutil.which",
        side_effect=lambda name: "/usr/bin/" + name,
    )
    def test_configure_is_target_native_canadian_cross(
        self, which, cmd_output, cmd
    ):
        with tempfile.TemporaryDirectory() as srcdir:
            self.package.configure(self.env, srcdir)

        command = cmd.call_args.args[0]
        command_env = cmd.call_args.kwargs["env"]
        self.assertIn("--build=x86_64-pc-linux-gnu", command)
        self.assertIn("--host=x86_64-pedigree", command)
        self.assertIn("--target=x86_64-pedigree", command)
        self.assertIn("--with-sysroot=/", command)
        self.assertIn("--with-native-system-header-dir=/usr/include", command)
        self.assertIn("--prefix=/usr", command)
        self.assertFalse(
            any(arg.startswith("--with-gxx-include-dir=") for arg in command)
        )
        self.assertIn("--with-as=/usr/bin/as", command)
        self.assertIn("--with-ld=/usr/bin/ld", command)
        dependency_prefix = self.env["PORTS_SYSROOT"] + "/usr"
        for dependency in ("gmp", "mpfr", "mpc"):
            self.assertIn(
                "--with-%s=%s" % (dependency, dependency_prefix), command
            )
        self.assertIn("--disable-bootstrap", command)
        self.assertIn("--enable-shared", command)
        self.assertIn("--enable-static", command)
        self.assertIn("--enable-symvers=gnu", command)
        self.assertNotIn("--disable-shared", command)
        self.assertIn("--enable-version-specific-runtime-libs", command)
        self.assertNotIn("--with-headers", command)
        self.assertEqual(command_env["CC_FOR_BUILD"], "/usr/bin/cc")
        self.assertEqual(command_env["CFLAGS_FOR_BUILD"], "-O2")
        self.assertEqual(command_env["CXXFLAGS_FOR_BUILD"], "-O2")
        self.assertEqual(command_env["CPPFLAGS_FOR_BUILD"], "")
        self.assertEqual(command_env["LDFLAGS_FOR_BUILD"], "")
        self.assertEqual(command_env["CC_FOR_TARGET"], self.env["CROSS_CC"])
        self.assertEqual(command_env["GCC_FOR_TARGET"], self.env["CROSS_CC"])
        self.assertEqual(command_env["gcc_cv_as"], self.env["CROSS_AS"])
        self.assertEqual(command_env["gcc_cv_ld"], self.env["CROSS_LD"])
        self.assertTrue(command_env["CFLAGS_FOR_TARGET"].endswith(" -fPIC"))
        self.assertTrue(
            command_env["CXXFLAGS_FOR_TARGET"].endswith(" -fPIC")
        )
        self.assertEqual(
            command_env["CONFIG_SITE"], self.env["TARGET_CONFIG_SITE"]
        )
        runtime_build = os.path.join(
            srcdir, "pedigree-build", self.env["CROSS_TARGET"], "libgcc"
        )
        self.assertEqual(
            command_env["LDFLAGS_FOR_TARGET"],
            f"-L{runtime_build} -Wl,-rpath-link,{runtime_build} "
            f"-Wl,--eh-frame-hdr {self.env['LDFLAGS']}",
        )
        self.assertEqual(command_env["LDFLAGS"], self.env["LDFLAGS"])

    def test_runtime_contract_includes_native_toolchain_and_math_libraries(self):
        expected = ["binutils", "libgmp", "libmpfr", "libmpc", "zlib"]
        self.assertEqual(self.package.build_requires(), expected)
        self.assertEqual(self.package.install_deps(), expected)

    def test_make_options_publish_only_target_configuration(self):
        options = self.package._make_options(self.env)

        self.assertEqual(len(options), 1)
        self.assertTrue(options[0].startswith("TOPLEVEL_CONFIGURE_ARGUMENTS="))
        self.assertIn("--host=x86_64-pedigree", options[0])
        self.assertIn("--with-sysroot=/", options[0])
        self.assertIn("--enable-version-specific-runtime-libs", options[0])
        self.assertIn("--enable-shared", options[0])
        self.assertIn("--enable-static", options[0])
        self.assertIn("--enable-symvers=gnu", options[0])
        self.assertNotIn("--with-gxx-include-dir", options[0])
        self.assertIn("--with-as=/usr/bin/as", options[0])
        self.assertNotIn(self.env["PORTS_SYSROOT"], options[0])
        self.assertNotIn(self.env["CROSS_BASE"], options[0])

    def test_patch_carries_current_musl_and_pedigree_contract(self):
        self.assertEqual(
            self.package.patches({}, "/source")[:2],
            ["pedigree-gcc.diff", "native-shared-runtime.diff"],
        )
        patch_path = os.path.join(
            os.path.dirname(__file__), "patches", "pedigree-gcc.diff"
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn("/usr/lib/ld-musl-x86_64.so.1", patch)
        self.assertIn("crtbeginT.o", patch)
        self.assertIn("file_end_indicate_exec_stack", patch)
        self.assertIn('extra_options="$extra_options gnu-user.opt"', patch)
        self.assertIn("%{pthread:-D_REENTRANT}", patch)
        self.assertIn("use_gcc_stdint=wrap", patch)
        self.assertIn("t-gthr-noweak", patch)
        self.assertNotIn("use_fixproto", patch)
        self.assertNotIn("config/override.m4", patch)

    def test_canadian_build_patch_is_limited_to_native_cxx_flags(self):
        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "canadian-build-flags.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn('CXXFLAGS="$(CXXFLAGS_FOR_BUILD)"', patch)
        self.assertNotIn("CXXFLAGS_FOR_TARGET", patch)

    def test_module_reader_honours_unavailable_madvise_probe(self):
        self.assertIn(
            "modules-madvise.diff", self.package.patches({}, "/source")
        )
        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "modules-madvise.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertEqual(patch.count("+#if defined (HAVE_MADVISE)"), 2)
        self.assertEqual(patch.count("if (madvise ("), 2)
        self.assertEqual(patch.count("-\t\tgoto fail;"), 1)
        self.assertEqual(patch.count("-    goto fail;"), 1)
        self.assertNotIn("ENOSYS", patch)
        self.assertNotIn("__pedigree__", patch)

    @staticmethod
    def _runtime_metadata(command, **kwargs):
        soname = os.path.basename(command[-1])
        prefix = "GLIBCXX_" if soname == "libstdc++.so.6" else "GCC_"
        return (
            " (SONAME) Library soname: [" + soname + "]\n"
            " (NEEDED) Shared library: [libgcc_s.so.1]\n"
            " Name: " + prefix + "3.4\n"
        )

    @mock.patch("packages.gcc.package.steps.cmd_output")
    def test_postdeploy_removes_libtool_metadata_and_requires_native_compiler(
        self, readelf
    ):
        readelf.side_effect = self._runtime_metadata
        with tempfile.TemporaryDirectory() as deploydir:
            bindir = os.path.join(deploydir, "usr", "bin")
            internal = os.path.join(
                deploydir,
                "usr",
                "lib",
                "gcc",
                self.env["CROSS_TARGET"],
                SOURCE_VERSION,
            )
            os.makedirs(bindir)
            os.makedirs(internal)
            for name in ("gcc", "g++"):
                open(os.path.join(bindir, name), "wb").close()
            runtimes = (
                "libstdc++.a",
                "libstdc++exp.a",
                "libsupc++.a",
                "libgcc.a",
                "libgcc_eh.a",
                "libgcc_s.so.1",
                "libstdc++.so.6.0.34",
                "libstdc++.so.6.0.34-gdb.py",
                "libstdc++.modules.json",
            )
            for name in ("cc1", "cc1plus", "liblto_plugin.so") + runtimes:
                open(os.path.join(internal, name), "wb").close()
            for name, target in (
                ("libstdc++.so", "libstdc++.so.6.0.34"),
                ("libstdc++.so.6", "libstdc++.so.6.0.34"),
            ):
                os.symlink(target, os.path.join(internal, name))
            linker_script = os.path.join(internal, "libgcc_s.so")
            with open(linker_script, "w", encoding="utf-8") as script:
                script.write("/* GNU ld script */\nGROUP ( libgcc_s.so.1 -lgcc )\n")
            legacy = os.path.join(deploydir, "usr", "lib", "libstdc++.so")
            with open(legacy, "wb") as old_runtime:
                old_runtime.write(b"legacy runtime")
            include = os.path.join(internal, "include", "c++")
            headers = (
                "algorithm",
                "cstdlib",
                os.path.join(self.env["CROSS_TARGET"], "bits", "c++config.h"),
            )
            for name in headers:
                header = os.path.join(include, name)
                os.makedirs(os.path.dirname(header), exist_ok=True)
                open(header, "wb").close()
            plugin_include = os.path.join(internal, "plugin", "include")
            os.makedirs(plugin_include)
            with open(
                os.path.join(plugin_include, "configargs.h"),
                "w",
                encoding="utf-8",
            ) as configargs:
                configargs.write(
                    'static const char configuration_arguments[] = '
                    '"--prefix=/usr --with-sysroot=/";\n'
                )
            archive = os.path.join(internal, "libstdc++.la")
            open(archive, "wb").close()

            self.package.postdeploy(self.env, "/source", deploydir)

            self.assertFalse(os.path.exists(archive))
            with open(legacy, "rb") as old_runtime:
                self.assertEqual(old_runtime.read(), b"legacy runtime")
            for soname in ("libgcc_s.so.1", "libstdc++.so.6"):
                public = os.path.join(deploydir, "usr", "lib", soname)
                self.assertEqual(
                    os.readlink(public),
                    "gcc/x86_64-pedigree/15.3.0/" + soname,
                )
                self.assertTrue(os.path.isfile(public))

            for name in headers:
                with self.subTest(missing_header=name):
                    header = os.path.join(include, name)
                    os.unlink(header)
                    with self.assertRaises(RuntimeError) as failure:
                        self.package.postdeploy(self.env, "/source", deploydir)
                    self.assertIn(
                        os.path.relpath(header, deploydir), str(failure.exception)
                    )
                    open(header, "wb").close()

            for name in runtimes:
                with self.subTest(unversioned_runtime=name):
                    private = os.path.join(internal, name)
                    public = os.path.join(deploydir, name)
                    os.rename(private, public)
                    with self.assertRaises(RuntimeError) as failure:
                        self.package.postdeploy(self.env, "/source", deploydir)
                    self.assertIn("not installed", str(failure.exception))
                    os.rename(public, private)

            for description, metadata, expected in (
                (
                    "SONAME",
                    " (SONAME) [libstdc++.so]\n Name: GLIBCXX_3.4\n",
                    "SONAME",
                ),
                (
                    "symbol versions",
                    " (SONAME) [libstdc++.so.6]\n",
                    "symbol versions",
                ),
                (
                    "shared unwinder",
                    " (SONAME) [libstdc++.so.6]\n Name: GLIBCXX_3.4\n",
                    "depend on shared",
                ),
            ):
                with self.subTest(missing=description):
                    readelf.side_effect = lambda command, **kwargs: (
                        metadata if command[-1].endswith("libstdc++.so.6")
                        else self._runtime_metadata(command)
                    )
                    with self.assertRaisesRegex(RuntimeError, expected):
                        self.package.postdeploy(self.env, "/source", deploydir)
            readelf.side_effect = self._runtime_metadata

            with open(linker_script, "w", encoding="utf-8") as script:
                script.write("GROUP ( -lgcc )\n")
            with self.assertRaisesRegex(RuntimeError, "libgcc_s.so linker script"):
                self.package.postdeploy(self.env, "/source", deploydir)
            with open(linker_script, "w", encoding="utf-8") as script:
                script.write("GROUP ( libgcc_s.so.1 -lgcc )\n")

            public = os.path.join(deploydir, "usr", "lib", "libgcc_s.so.1")
            os.unlink(public)
            with open(public, "wb") as stale_runtime:
                stale_runtime.write(b"stale runtime")
            with self.assertRaisesRegex(RuntimeError, "conflicting GCC runtime"):
                self.package.postdeploy(self.env, "/source", deploydir)
            os.unlink(public)

            with open(
                os.path.join(plugin_include, "configargs.h"),
                "w",
                encoding="utf-8",
            ) as configargs:
                configargs.write(self.env["APPS_BASE"])
            with self.assertRaisesRegex(RuntimeError, "contains build paths"):
                self.package.postdeploy(self.env, "/source", deploydir)


if __name__ == "__main__":
    unittest.main()
