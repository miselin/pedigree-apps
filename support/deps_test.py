import os
import tempfile
import unittest
from unittest import mock

from . import deps


class DepsTest(unittest.TestCase):
    def package(self, name, requires=(), version="1.0"):
        package = mock.MagicMock()
        package.name.return_value = name
        package.version.return_value = version
        package.build_requires.return_value = list(requires)
        return package

    def test_simple_deps(self):
        packages = {
            "package1": self.package("package1"),
            "package2": self.package("package2", ("package1",)),
        }
        self.assertEqual(
            [name for name, _ in deps.sort_dependencies(packages)],
            ["package1", "package2"],
        )

    def test_cyclic_deps(self):
        packages = {
            "package1": self.package("package1", ("package2",)),
            "package2": self.package("package2", ("package1",)),
        }
        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            deps.sort_dependencies(packages)

    def test_implicit_deps(self):
        packages = {
            "package1": self.package("package1"),
            "package2": self.package("package2", ("package1",)),
            "package3": self.package("package3", ("package2",)),
        }
        selected = deps.select_with_dependencies(packages, ("package3",))
        self.assertEqual(
            [name for name, _ in selected],
            ["package1", "package2", "package3"],
        )

    def test_prepare_sysroot_stages_dependency(self):
        dependency = self.package("dependency")
        package = self.package("package", ("dependency",))
        packages = {"dependency": dependency, "package": package}
        with tempfile.TemporaryDirectory() as temporary:
            root = os.path.join(
                temporary, "output", "dependency", "1.0", "root", "usr", "include"
            )
            os.makedirs(root)
            with open(
                os.path.join(temporary, "output", "dependency", "1.0", ".complete"),
                "w",
                encoding="utf-8",
            ) as marker:
                marker.write("dependency-1.0\n")
            with open(os.path.join(root, "dependency.h"), "w", encoding="utf-8") as f:
                f.write("/* dependency */\n")
            env = {
                "BUILD_BASE": os.path.join(temporary, "build"),
                "OUTPUT_BASE": os.path.join(temporary, "output"),
                "LDFLAGS": "-Wl,test",
            }
            prepared = deps.prepare_sysroot(packages, package, env)
            self.assertTrue(
                os.path.isfile(
                    os.path.join(
                        prepared["PORTS_SYSROOT"], "usr", "include", "dependency.h"
                    )
                )
            )
            self.assertIn(prepared["PORTS_SYSROOT"], prepared["CPPFLAGS"])


if __name__ == "__main__":
    unittest.main()
