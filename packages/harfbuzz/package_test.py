import os
import tempfile
import unittest

from .package import HarfbuzzPackage


class HarfbuzzPackageTest(unittest.TestCase):
    def test_cmake_config_omits_disabled_icu_module(self):
        package = HarfbuzzPackage(__file__)
        self.assertEqual(
            package.patches({}, ""), ["pedigree-cmake-icu-target.diff"]
        )

        with tempfile.TemporaryDirectory() as srcdir:
            source_dir = os.path.join(srcdir, "src")
            os.makedirs(source_dir)
            meson_build = os.path.join(source_dir, "meson.build")
            with open(meson_build, "w", encoding="utf-8") as source:
                source.write("\n" * 1151)
                source.write(
                    "cmake_config.set('PACKAGE_CMAKE_INSTALL_BINDIR', "
                    "'${PACKAGE_PREFIX_DIR}/@0@'.format(cmake_install_bindir))\n"
                    "cmake_config.set('PACKAGE_INCLUDE_INSTALL_DIR', "
                    "'${PACKAGE_PREFIX_DIR}/@0@/@1@'.format("
                    "cmake_install_includedir, meson.project_name()))\n"
                    "cmake_config.set('HARFBUZZ_VERSION', meson.project_version())\n"
                    "cmake_config.set('HB_HAVE_GOBJECT', "
                    "have_gobject ? 'YES' : 'NO')\n"
                    "cmake_config.set('HB_LIBRARY_TYPE', "
                    "get_option('default_library') == 'static' ? "
                    "'STATIC' : 'SHARED')\n"
                    "cmake_config.set('HB_HAS_IMPORT_LIBRARY', 'NO')\n"
                    "cmake_config.set('HB_IMPLIB_PREFIX', '')\n"
                )

            cmake_config = os.path.join(
                source_dir, "harfbuzz-config.cmake.in"
            )
            with open(cmake_config, "w", encoding="utf-8") as source:
                source.write("\n" * 18)
                source.write(
                    '  INTERFACE_INCLUDE_DIRECTORIES '
                    '"@PACKAGE_INCLUDE_INSTALL_DIR@")\n'
                    "_harfbuzz_set_imported_library("
                    "harfbuzz::harfbuzz harfbuzz)\n\n"
                    "add_library(harfbuzz::icu @HB_LIBRARY_TYPE@ IMPORTED)\n"
                    "set_target_properties(harfbuzz::icu PROPERTIES\n"
                    '  INTERFACE_INCLUDE_DIRECTORIES '
                    '"@PACKAGE_INCLUDE_INSTALL_DIR@"\n'
                    '  INTERFACE_LINK_LIBRARIES "harfbuzz::harfbuzz")\n'
                    "_harfbuzz_set_imported_library("
                    "harfbuzz::icu harfbuzz-icu)\n\n"
                    "add_library(harfbuzz::subset @HB_LIBRARY_TYPE@ IMPORTED)\n"
                    "set_target_properties(harfbuzz::subset PROPERTIES\n"
                )

            package.patch({"PATCH": "/usr/bin/patch"}, srcdir)

            with open(meson_build, encoding="utf-8") as source:
                patched_meson = source.read()
            self.assertIn(
                "cmake_config.set('HB_HAVE_ICU_MODULE', "
                "have_icu and not have_icu_builtin ? 'YES' : 'NO')",
                patched_meson,
            )

            with open(cmake_config, encoding="utf-8") as source:
                patched_config = source.read()
            self.assertIn("if (@HB_HAVE_ICU_MODULE@)", patched_config)
            self.assertIn(
                "_harfbuzz_set_imported_library("
                "harfbuzz::icu harfbuzz-icu)\nendif ()",
                patched_config,
            )


if __name__ == "__main__":
    unittest.main()
