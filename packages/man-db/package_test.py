import os
import tempfile
import unittest
from unittest import mock

from support import steps

from .package import ManDbPackage


class ManDbPackageTest(unittest.TestCase):

    def setUp(self):
        self.package = ManDbPackage(__file__)

    def test_runtime_contract_includes_formatter_and_available_tools(self):
        self.assertEqual(
            self.package.build_requires(),
            ["gdbm", "libpipeline", "mandoc", "zlib"],
        )
        self.assertEqual(
            self.package.install_deps(),
            [
                "gdbm",
                "grep",
                "gzip",
                "less",
                "libpipeline",
                "mandoc",
                "zlib",
            ],
        )

    def test_gnulib_pselect_has_a_pedigree_compatible_null_definition(self):
        patches = self.package.patches({}, "/source")
        self.assertEqual(
            patches,
            [
                "gnulib-pselect-stddef.diff",
                "mandoc-default-preprocessor.diff",
            ],
        )
        patch_path = os.path.join(
            os.path.dirname(__file__), "patches", patches[0]
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            self.assertIn("+#include <stddef.h>", patch_file.read())

    def test_mandoc_profile_skips_external_default_preprocessors(self):
        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "mandoc-default-preprocessor.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn(
            "+#if defined(__pedigree__) || defined(__PEDIGREE__)", patch
        )
        self.assertIn('+#  define DEFAULT_MANROFFSEQ ""', patch)
        self.assertIn("+#else", patch)
        self.assertIn('#  define DEFAULT_MANROFFSEQ "t"', patch)

    def test_mandoc_profile_ignores_explicit_preprocessor_sequences(self):
        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "mandoc-default-preprocessor.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        guard = "+#if defined(__pedigree__) || defined(__PEDIGREE__)"
        branch_start = patch.rindex(guard)
        branch_end = patch.index("+#else", branch_start)
        pedigree_branch = patch[branch_start:branch_end]

        self.assertIn("'\\\" t", pedigree_branch)
        self.assertIn("MANROFFSEQ", pedigree_branch)
        self.assertIn("database filters", pedigree_branch)
        self.assertIn("and -p", pedigree_branch)
        self.assertNotIn("xstrndup (pp_string", pedigree_branch)
        self.assertNotIn("pipecmd_new_argstr", pedigree_branch)

        non_pedigree_end = patch.index("+#endif", branch_end)
        non_pedigree_branch = patch[branch_end:non_pedigree_end]
        self.assertIn("/* Add preprocessors.", non_pedigree_branch)
        self.assertIn("free (pp_string_initial);", non_pedigree_branch)

    @mock.patch.object(steps, "run_configure")
    def test_configure_never_executes_target_formatter(self, run_configure):
        env = {"TARGET_CONFIG_SITE": "/workspace/config.site"}
        with tempfile.TemporaryDirectory() as source:
            libtool_path = os.path.join(source, "libtool")
            with open(libtool_path, "w", encoding="utf-8") as libtool:
                libtool.write(
                    "hardcode_into_libs=yes\n"
                    'hardcode_libdir_flag_spec="\\$wl-rpath '
                    '\\$wl\\$libdir"\n'
                    "hardcode_action=immediate\n"
                )

            self.package.configure(env, source)

            with open(libtool_path, encoding="utf-8") as libtool:
                libtool_contents = libtool.read()

        self.assertEqual(env["man_cv_prog_gnu_nroff"], "no")
        self.assertEqual(env["man_cv_prog_heirloom_nroff"], "no")
        self.assertEqual(env["man_cv_prog_nroff_macro"], "-mandoc")
        self.assertEqual(env["man_cv_prog_nroff_warnings"], "no")
        self.assertEqual(env["ac_cv_prog_troff"], "")

        options = run_configure.call_args.kwargs["extra_config"]
        self.assertIn("--with-nroff=/usr/bin/mandoc", options)
        self.assertIn("--with-pager=/usr/bin/less", options)
        self.assertIn("--with-gzip=/usr/bin/gzip", options)
        self.assertIn("--disable-cache-owner", options)
        self.assertIn("--disable-dependency-tracking", options)
        self.assertIn("--disable-manual", options)
        self.assertIn("--disable-nls", options)
        self.assertIn("--disable-rpath", options)
        self.assertIn("--disable-setuid", options)
        self.assertIn("--disable-threads", options)
        self.assertIn("hardcode_into_libs=no", libtool_contents)
        self.assertIn('hardcode_libdir_flag_spec=""', libtool_contents)
        self.assertIn("hardcode_action=unsupported", libtool_contents)
        self.assertNotIn("rpath \\$wl\\$libdir", libtool_contents)
        for tool in (
            "browser",
            "eqn",
            "neqn",
            "tbl",
            "col",
            "vgrind",
            "refer",
            "grap",
            "pic",
            "compress",
            "bzip2",
            "xz",
            "lzma",
            "lzip",
            "zstd",
        ):
            with self.subTest(tool=tool):
                self.assertIn("--with-%s=" % tool, options)


if __name__ == "__main__":
    unittest.main()
