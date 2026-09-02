import os
import runpy
import unittest


class DeferredInfrastructureTest(unittest.TestCase):

    def metadata(self, package):
        repository = os.path.dirname(os.path.dirname(__file__))
        return runpy.run_path(
            os.path.join(repository, "packages", package, "package.py")
        )

    def test_current_upstream_versions_are_recorded(self):
        expected = {
            "fuse": "3.18.2",
            "grub2": "2.14",
            "libbind": "6.0",
            "llvm": "22.1.8",
            "newlib": "4.6.0.20260123",
            "pth": "2.0.7",
            "python27": "2.7.18",
            "qemu": "11.1.1",
        }
        for package, version in expected.items():
            with self.subTest(package=package):
                self.assertEqual(
                    self.metadata(package)["UPSTREAM_VERSION"], version
                )

    def test_mainline_artifacts_require_explicit_package_exports(self):
        expected_contracts = {
            "pedigree-base": ("versioned FHS", "mutable"),
            "pedigree-devel": ("versioned SDK/sysroot", "compiler prefix"),
            "pedigree-kernel": ("aggregate build target", "versioned /boot"),
            "pedigree-modules": ("initrd.manifest", "explicit module/initrd export"),
        }
        for package, phrases in expected_contracts.items():
            reason = self.metadata(package)["DISABLED_REASON"]
            with self.subTest(package=package):
                for phrase in phrases:
                    self.assertIn(phrase, reason)

    def test_unsupported_abis_are_not_described_as_build_failures(self):
        expected_contracts = {
            "fuse": ("/dev/fuse", "kernel protocol ABI"),
            "libbind": ("duplicates musl", "cannot safely share"),
            "newlib": ("final sysroot ABI is musl", "incompatible libc"),
            "pth": ("ENOSYS stubs", "fake semantics is unsafe"),
        }
        for package, phrases in expected_contracts.items():
            reason = self.metadata(package)["DISABLED_REASON"]
            with self.subTest(package=package):
                for phrase in phrases:
                    self.assertIn(phrase, reason)


if __name__ == "__main__":
    unittest.main()
