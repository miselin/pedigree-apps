import os
import tempfile
import unittest

from .package import OpensslPackage


class OpensslPackageTest(unittest.TestCase):
    def setUp(self):
        self.env = {
            "CROSS_BASE": "/opt/pedigree",
            "PORTS_SYSROOT": "/workspace/.build/x86_64/sysroots/openssl",
        }

    def _write_libcrypto(self, deploydir, diagnostic):
        libdir = os.path.join(deploydir, "usr", "lib")
        os.makedirs(libdir)
        path = os.path.join(libdir, "libcrypto.so.3")
        with open(path, "wb") as library:
            library.write(b"ELF fixture\0" + diagnostic + b"\0tail")

    def test_runtime_dependencies_include_perl_tools(self):
        self.assertEqual(
            OpensslPackage(__file__).install_deps(), ["zlib", "perl"]
        )

    def test_target_patch_uses_self_hosted_build_descriptor(self):
        with tempfile.TemporaryDirectory() as srcdir:
            os.makedirs(os.path.join(srcdir, "Configurations"))
            crypto = os.path.join(srcdir, "crypto")
            os.makedirs(crypto)
            build_info = os.path.join(crypto, "build.info")
            with open(build_info, "w", encoding="utf-8") as source:
                source.write(
                    "\n" * 112
                    + (
                        "SOURCE[../libcrypto]=$UPLINKSRC\n"
                        "DEFINE[../libcrypto]=$UPLINKDEF\n"
                        "\n"
                        "DEPEND[info.o]=buildinf.h\n"
                        "DEPEND[cversion.o]=buildinf.h\n"
                        'GENERATE[buildinf.h]=../util/mkbuildinf.pl '
                        '"$(CC) $(LIB_CFLAGS) $(CPPFLAGS_Q)" '
                        '"$(PLATFORM)"\n'
                        "\n"
                        "GENERATE[uplink-x86.S]=../ms/uplink-x86.pl\n"
                        "GENERATE[uplink-x86_64.s]="
                        "../ms/uplink-x86_64.pl\n"
                    )
                )

            OpensslPackage(__file__).patch(
                {"PATCH": "/usr/bin/patch"}, srcdir
            )

            with open(build_info, encoding="utf-8") as source:
                generated = source.read()
            self.assertIn(
                'mkbuildinf.pl "gcc" "$(PLATFORM)"', generated
            )
            self.assertNotIn("$(CC)", generated)
            self.assertNotIn("$(LIB_CFLAGS)", generated)
            self.assertNotIn("$(CPPFLAGS_Q)", generated)

            target = os.path.join(
                srcdir, "Configurations", "50-pedigree.conf"
            )
            with open(target, encoding="utf-8") as source:
                configuration = source.read()
            self.assertNotIn("NO_RECVMMSG", configuration)

    def test_postdeploy_accepts_target_safe_compiler_diagnostic(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self._write_libcrypto(deploydir, b"compiler: gcc")

            OpensslPackage(__file__).postdeploy(
                self.env, "", deploydir
            )

    def test_postdeploy_rejects_build_paths_in_compiler_diagnostic(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self._write_libcrypto(
                deploydir,
                (
                    "compiler: %s/bin/x86_64-pedigree-gcc -I%s/usr/include"
                    % (self.env["CROSS_BASE"], self.env["PORTS_SYSROOT"])
                ).encode(),
            )

            with self.assertRaisesRegex(
                RuntimeError, "compiler diagnostic contains build paths"
            ):
                OpensslPackage(__file__).postdeploy(
                    self.env, "", deploydir
                )

    def test_postdeploy_requires_target_safe_compiler_diagnostic(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self._write_libcrypto(deploydir, b"compiler: clang")

            with self.assertRaisesRegex(
                RuntimeError, "compiler diagnostic was not target-safe"
            ):
                OpensslPackage(__file__).postdeploy(
                    self.env, "", deploydir
                )


if __name__ == "__main__":
    unittest.main()
