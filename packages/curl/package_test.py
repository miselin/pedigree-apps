import os
import tempfile
import unittest
from unittest import mock

from .package import CurlPackage


class CurlPackageTest(unittest.TestCase):
    @mock.patch("packages.curl.package.steps.run_configure")
    def test_configure_uses_system_ca_bundle(self, run_configure):
        package = CurlPackage(__file__)

        package.configure({}, "/source")

        options = run_configure.call_args.kwargs["extra_config"]
        self.assertIn("--with-ca-bundle=/etc/ssl/cert.pem", options)
        self.assertIn("--without-ca-path", options)
        self.assertNotIn("--without-ca-bundle", options)

    def test_postdeploy_sanitizes_curl_config_build_metadata(self):
        with tempfile.TemporaryDirectory() as deploydir:
            bindir = os.path.join(deploydir, "usr", "bin")
            libdir = os.path.join(deploydir, "usr", "lib")
            pkgconfig_dir = os.path.join(libdir, "pkgconfig")
            os.makedirs(bindir)
            os.makedirs(pkgconfig_dir)

            env = {
                "APPS_BASE": "/workspace",
                "CROSS_BASE": "/opt/pedigree",
                "CROSS_CC": "/opt/pedigree/bin/x86_64-pedigree-gcc",
                "CROSS_CXX": "/opt/pedigree/bin/x86_64-pedigree-g++",
                "CROSS_CPP": "/opt/pedigree/bin/x86_64-pedigree-cpp",
                "CROSS_AS": "/opt/pedigree/bin/x86_64-pedigree-as",
                "CROSS_LD": "/opt/pedigree/bin/x86_64-pedigree-ld",
                "CROSS_AR": "/opt/pedigree/bin/x86_64-pedigree-ar",
                "CROSS_RANLIB": (
                    "/opt/pedigree/bin/x86_64-pedigree-ranlib"
                ),
                "CROSS_STRIP": (
                    "/opt/pedigree/bin/x86_64-pedigree-strip"
                ),
                "PORTS_SYSROOT": (
                    "/workspace/.build/x86_64/sysroots/curl"
                ),
                "TARGET_SYSROOT": "/opt/pedigree/x86_64-pedigree",
            }
            config = os.path.join(bindir, "curl-config")
            with open(config, "w", encoding="utf-8") as script:
                script.write(
                    "#!/bin/sh\n"
                    "case \"$1\" in\n"
                    "--cc) echo '%s' ;;\n"
                    "--static-libs) echo \"/usr/lib/libcurl.a "
                    "-L%s/usr/lib -Wl,-rpath-link,%s/usr/lib "
                    "-L/usr/lib\" ;;\n"
                    "--configure) echo \" '--host=x86_64-pedigree' "
                    "'--prefix=/usr' '--with-sysroot=%s' "
                    "'CC=%s' 'CXX=%s' 'CPP=%s' 'AS=%s' 'LD=%s' "
                    "'AR=%s' 'RANLIB=%s' 'STRIP=%s' "
                    "'CFLAGS=--sysroot=%s "
                    "-I%s/usr/include -I/usr/include/curl'\" ;;\n"
                    "esac\n"
                    % (
                        env["CROSS_CC"],
                        env["PORTS_SYSROOT"],
                        env["PORTS_SYSROOT"],
                        env["PORTS_SYSROOT"],
                        env["CROSS_CC"],
                        env["CROSS_CXX"],
                        env["CROSS_CPP"],
                        env["CROSS_AS"],
                        env["CROSS_LD"],
                        env["CROSS_AR"],
                        env["CROSS_RANLIB"],
                        env["CROSS_STRIP"],
                        env["TARGET_SYSROOT"],
                        env["PORTS_SYSROOT"],
                    )
                )
            metadata_paths = (
                os.path.join(pkgconfig_dir, "libcurl.pc"),
                os.path.join(libdir, "libcurl.la"),
            )
            for metadata_path in metadata_paths:
                with open(metadata_path, "w", encoding="utf-8") as metadata:
                    metadata.write(
                        "Libs.private: -L%s/usr/lib "
                        "-Wl,-rpath-link,%s/usr/lib -lz\n"
                        % (env["PORTS_SYSROOT"], env["PORTS_SYSROOT"])
                    )

            CurlPackage(__file__).postdeploy(env, "", deploydir)

            with open(config, encoding="utf-8") as script:
                contents = script.read()
            self.assertIn("echo 'gcc'", contents)
            self.assertIn("'CC=gcc'", contents)
            self.assertIn("'CXX=g++'", contents)
            self.assertIn("'CPP=cpp'", contents)
            self.assertIn("'AS=as'", contents)
            self.assertIn("'LD=ld'", contents)
            self.assertIn("'AR=ar'", contents)
            self.assertIn("'RANLIB=ranlib'", contents)
            self.assertIn("'STRIP=strip'", contents)
            self.assertIn("'--prefix=/usr'", contents)
            self.assertIn("-L/usr/lib", contents)
            self.assertIn("-I/usr/include/curl", contents)
            self.assertNotIn("--with-sysroot", contents)
            self.assertNotIn("--sysroot", contents)
            self.assertNotIn("rpath-link", contents)
            self.assertNotIn(env["CROSS_BASE"], contents)
            self.assertNotIn(env["PORTS_SYSROOT"], contents)

            for metadata_path in metadata_paths:
                with open(metadata_path, encoding="utf-8") as metadata:
                    metadata_contents = metadata.read()
                self.assertIn("-L/usr/lib", metadata_contents)
                self.assertNotIn("rpath-link", metadata_contents)
                self.assertNotIn(env["PORTS_SYSROOT"], metadata_contents)


if __name__ == "__main__":
    unittest.main()
