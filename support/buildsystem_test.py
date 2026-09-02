import os
import tempfile
import textwrap
import unittest

from . import buildsystem


class BuildSystemTest(unittest.TestCase):
    def test_load_packages_uses_python3_imports(self):
        with tempfile.TemporaryDirectory() as temporary:
            package_dir = os.path.join(temporary, "example")
            os.makedirs(package_dir)
            with open(
                os.path.join(package_dir, "package.py"), "w", encoding="utf-8"
            ) as package_file:
                package_file.write(
                    textwrap.dedent(
                        """
                        from support import buildsystem

                        class Example(buildsystem.Package):
                            def name(self):
                                return "example"
                            def version(self):
                                return "1.0"
                        """
                    )
                )
            packages = buildsystem.load_packages({"SOURCE_BASE": temporary})
            self.assertEqual(packages["example"].version(), "1.0")

    def test_package_check_rejects_non_fhs_usr_documentation(self):
        with tempfile.TemporaryDirectory() as deploydir:
            os.makedirs(os.path.join(deploydir, "usr", "doc"))
            package = buildsystem.Package(__file__)
            with self.assertRaisesRegex(RuntimeError, "non-FHS /usr paths: doc"):
                package.check({}, "", deploydir)

    def test_load_packages_includes_explicit_dynamic_types(self):
        with tempfile.TemporaryDirectory() as temporary:
            package_dir = os.path.join(temporary, "dynamic")
            os.makedirs(package_dir)
            with open(
                os.path.join(package_dir, "package.py"), "w", encoding="utf-8"
            ) as package_file:
                package_file.write(
                    textwrap.dedent(
                        """
                        from support import buildsystem

                        class DynamicBase(buildsystem.Package):
                            def name(self):
                                return ""
                            def version(self):
                                return ""

                        dynamic = type(
                            "DynamicPackage",
                            (DynamicBase,),
                            {
                                "name": lambda self: "dynamic",
                                "version": lambda self: "1.0",
                            },
                        )
                        extra_types = {"DynamicPackage": dynamic}
                        """
                    )
                )
            packages = buildsystem.load_packages({"SOURCE_BASE": temporary})
            self.assertEqual(packages["dynamic"].version(), "1.0")

    def test_load_packages_skips_explicitly_deferred_port(self):
        with tempfile.TemporaryDirectory() as temporary:
            package_dir = os.path.join(temporary, "deferred")
            os.makedirs(package_dir)
            with open(
                os.path.join(package_dir, "package.py"), "w", encoding="utf-8"
            ) as package_file:
                package_file.write(
                    textwrap.dedent(
                        """
                        from support import buildsystem

                        DISABLED_REASON = "not ready"

                        class Deferred(buildsystem.Package):
                            def name(self):
                                return "deferred"
                            def version(self):
                                return "1.0"
                        """
                    )
                )
            packages = buildsystem.load_packages({"SOURCE_BASE": temporary})
            self.assertNotIn("deferred", packages)


if __name__ == "__main__":
    unittest.main()
