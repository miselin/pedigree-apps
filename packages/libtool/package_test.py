import os
import tempfile
import unittest

from .package import LibtoolPackage


class LibtoolPackageTest(unittest.TestCase):
    def setUp(self):
        self.env = {
            "APPS_BASE": "/workspace",
            "BUILD_BASE": "/workspace/.build/x86_64",
            "OUTPUT_BASE": "/workspace/newpacks/x86_64",
            "DOWNLOAD_TEMP": "/workspace/downloads",
            "CROSS_BASE": "/opt/pedigree",
            "CROSS_TARGET": "x86_64-pedigree",
            "TARGET_SYSROOT": "/opt/pedigree/x86_64-pedigree",
            "PORTS_SYSROOT": "/workspace/.build/x86_64/sysroots/libtool",
            "CROSS_CC": "/opt/pedigree/bin/x86_64-pedigree-gcc",
            "CROSS_CXX": "/opt/pedigree/bin/x86_64-pedigree-g++",
            "CROSS_CPP": "/opt/pedigree/bin/x86_64-pedigree-cpp",
            "CROSS_AS": "/opt/pedigree/bin/x86_64-pedigree-as",
            "CROSS_LD": "/opt/pedigree/bin/x86_64-pedigree-ld",
            "CROSS_AR": "/opt/pedigree/bin/x86_64-pedigree-ar",
            "CROSS_RANLIB": "/opt/pedigree/bin/x86_64-pedigree-ranlib",
            "CROSS_STRIP": "/opt/pedigree/bin/x86_64-pedigree-strip",
        }

    def _write_metadata(self, deploydir, driver_content):
        bindir = os.path.join(deploydir, "usr", "bin")
        libdir = os.path.join(deploydir, "usr", "lib")
        os.makedirs(bindir)
        os.makedirs(libdir)

        driver = os.path.join(bindir, "libtool")
        with open(driver, "w", encoding="utf-8") as script:
            script.write(driver_content)

        archive = os.path.join(libdir, "libltdl.la")
        with open(archive, "w", encoding="utf-8") as metadata:
            metadata.write(
                "dependency_libs=' -L%s/usr/lib '\n"
                "libdir='/usr/lib'\n"
                % self.env["PORTS_SYSROOT"]
            )
        return driver, archive

    def test_postdeploy_rebases_driver_for_native_target_tools(self):
        with tempfile.TemporaryDirectory() as deploydir:
            driver, archive = self._write_metadata(
                deploydir,
                "#! /bin/bash\n"
                "host_alias=x86_64-pedigree\n"
                'lt_sysroot=%s\n'
                'AS="%s"\n'
                'OBJDUMP="x86_64-pedigree-objdump"\n'
                'NM="%s/bin/x86_64-pedigree-nm -B"\n'
                'AR="%s"\n'
                'STRIP="%s"\n'
                'RANLIB="%s"\n'
                'LTCC="%s"\n'
                'LD="%s"\n'
                'CC="%s"\n'
                'CXX="%s"\n'
                'sys_lib_search_path_spec="%s/lib/gcc/x86_64-pedigree/'
                '15.3.0 %s/lib"\n'
                'predep_objects="%s/lib/gcc/x86_64-pedigree/15.3.0/'
                'crti.o"\n'
                % (
                    self.env["PORTS_SYSROOT"],
                    self.env["CROSS_AS"],
                    self.env["CROSS_BASE"],
                    self.env["CROSS_AR"],
                    self.env["CROSS_STRIP"],
                    self.env["CROSS_RANLIB"],
                    self.env["CROSS_CC"],
                    self.env["CROSS_LD"],
                    self.env["CROSS_CC"],
                    self.env["CROSS_CXX"],
                    self.env["CROSS_BASE"],
                    self.env["TARGET_SYSROOT"],
                    self.env["CROSS_BASE"],
                ),
            )

            LibtoolPackage(__file__).postdeploy(
                self.env, "/workspace/.build/x86_64/work/libtool", deploydir
            )

            with open(driver, encoding="utf-8") as script:
                content = script.read()
            for assignment in (
                'AS="as"',
                'OBJDUMP="objdump"',
                'NM="nm -B"',
                'AR="ar"',
                'STRIP="strip"',
                'RANLIB="ranlib"',
                'LTCC="gcc"',
                'LD="ld"',
                'CC="gcc"',
                'CXX="g++"',
            ):
                self.assertIn(assignment, content)
            self.assertIn("host_alias=x86_64-pedigree", content)
            self.assertIn(
                'sys_lib_search_path_spec="/usr/lib/gcc/'
                'x86_64-pedigree/15.3.0 /usr/lib"',
                content,
            )
            self.assertIn(
                'predep_objects="/usr/lib/gcc/'
                'x86_64-pedigree/15.3.0/crti.o"',
                content,
            )
            self.assertIn("lt_sysroot=\n", content)
            self.assertNotIn(self.env["CROSS_BASE"], content)
            self.assertNotIn(self.env["PORTS_SYSROOT"], content)
            self.assertNotIn("x86_64-pedigree-gcc", content)
            self.assertNotIn("x86_64-pedigree-objdump", content)

            with open(archive, encoding="utf-8") as metadata:
                archive_content = metadata.read()
            self.assertIn("dependency_libs=''", archive_content)
            self.assertIn("libdir='/usr/lib'", archive_content)
            self.assertNotIn(self.env["PORTS_SYSROOT"], archive_content)

    def test_postdeploy_rejects_unrecognized_build_path_leaks(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self._write_metadata(
                deploydir,
                "#! /bin/bash\n"
                "generated_file=%s/unexpected/libtool-state\n"
                % self.env["OUTPUT_BASE"],
            )

            with self.assertRaisesRegex(
                RuntimeError, "Libtool metadata contains cross-build paths"
            ):
                LibtoolPackage(__file__).postdeploy(
                    self.env,
                    "/workspace/.build/x86_64/work/libtool",
                    deploydir,
                )


if __name__ == "__main__":
    unittest.main()
