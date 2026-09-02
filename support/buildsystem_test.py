import os
import tempfile
import textwrap
import unittest
from unittest import mock

from . import buildsystem


class BuildSystemTest(unittest.TestCase):
    class ScriptPackage(buildsystem.Package):
        def __init__(self, package_path, name="example", dependencies=()):
            super().__init__(package_path)
            self._name = name
            self._dependencies = list(dependencies)

        def name(self):
            return self._name

        def install_deps(self):
            return self._dependencies

    def write_script(self, deploydir, shebang, relative="usr/bin/example"):
        path = os.path.join(deploydir, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as script:
            script.write(shebang + "\n")
        os.chmod(path, 0o755)
        return path

    def test_package_patch_rejects_fuzzy_application(self):
        with tempfile.TemporaryDirectory() as temporary:
            package_dir = os.path.join(temporary, "example")
            patches_dir = os.path.join(package_dir, "patches")
            os.makedirs(patches_dir)
            package_path = os.path.join(package_dir, "package.py")
            patch_path = os.path.join(patches_dir, "fix.diff")
            with open(package_path, "w", encoding="utf-8"):
                pass
            with open(patch_path, "wb") as patch_file:
                patch_file.write(b"patch")

            package = buildsystem.Package(package_path)
            package.patches = mock.Mock(return_value=["fix.diff"])
            with mock.patch(
                "support.buildsystem.subprocess.check_call"
            ) as check_call:
                package.patch({"PATCH": "/usr/bin/patch"}, temporary)

        self.assertEqual(
            check_call.call_args.args[0],
            ["/usr/bin/patch", "--batch", "--fuzz=0", "-p1"],
        )

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

    def test_package_check_rejects_legacy_system_root(self):
        with tempfile.TemporaryDirectory() as deploydir:
            os.makedirs(os.path.join(deploydir, "system"))
            package = buildsystem.Package(__file__)
            with self.assertRaisesRegex(RuntimeError, "top-level paths: system"):
                package.check({}, "", deploydir)

    def test_package_check_rejects_build_path_in_metadata(self):
        with tempfile.TemporaryDirectory() as deploydir:
            metadata_dir = os.path.join(deploydir, "usr", "lib")
            os.makedirs(metadata_dir)
            with open(
                os.path.join(metadata_dir, "example.la"),
                "w",
                encoding="utf-8",
            ) as metadata:
                metadata.write(
                    "dependency_libs='-L/workspace/.build/sysroot/usr/lib'\n"
                )
            package = buildsystem.Package(__file__)
            with self.assertRaisesRegex(
                RuntimeError, "metadata contains build paths"
            ):
                package.check(
                    {"APPS_BASE": "/workspace", "CROSS_BASE": "/opt/pedigree"},
                    "",
                    deploydir,
                )

    def test_package_check_rejects_build_rpath(self):
        with tempfile.TemporaryDirectory() as deploydir:
            binary_dir = os.path.join(deploydir, "usr", "bin")
            os.makedirs(binary_dir)
            binary = os.path.join(binary_dir, "example")
            with open(binary, "wb") as executable:
                executable.write(b"\x7fELF")
            readelf_result = mock.Mock(
                stdout=(
                    " 0x000000000000001d (RUNPATH) Library runpath: "
                    "[/workspace/.build/sysroot/usr/lib]\n"
                )
            )
            package = buildsystem.Package(__file__)
            with mock.patch(
                "support.buildsystem.subprocess.run",
                return_value=readelf_result,
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "ELF contains build RPATH"
                ):
                    package.check(
                        {
                            "APPS_BASE": "/workspace",
                            "CROSS_BASE": "/opt/pedigree",
                            "CROSS_TARGET": "x86_64-pedigree",
                        },
                        "",
                        deploydir,
                    )

    def test_package_check_accepts_base_shell_without_runtime_dependency(self):
        for shebang in ("#!/bin/sh", "#!/bin/bash", "#!/usr/bin/env bash"):
            with self.subTest(
                shebang=shebang
            ), tempfile.TemporaryDirectory() as deploydir:
                self.write_script(deploydir, shebang)
                package = self.ScriptPackage(__file__)
                package.check({}, "", deploydir)

    def test_package_check_requires_non_base_script_provider(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self.write_script(deploydir, "#!/usr/bin/env python3")
            package = self.ScriptPackage(__file__)
            with self.assertRaisesRegex(
                RuntimeError, "requires runtime provider python3"
            ):
                package.check({}, "", deploydir)

            package = self.ScriptPackage(__file__, dependencies=("python3",))
            package.check({}, "", deploydir)

    def test_package_check_accepts_interpreter_provided_by_same_package(self):
        for package_name, shebang in (
            ("perl", "#!/usr/bin/perl"),
            ("slang", "#!/usr/bin/env slsh"),
        ):
            with self.subTest(
                package=package_name
            ), tempfile.TemporaryDirectory() as deploydir:
                self.write_script(deploydir, shebang)
                package = self.ScriptPackage(__file__, name=package_name)
                package.check({}, "", deploydir)

    def test_package_check_rejects_unknown_executable_interpreter(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self.write_script(deploydir, "#!/usr/bin/ruby")
            package = self.ScriptPackage(__file__)
            with self.assertRaisesRegex(
                RuntimeError, "unsupported executable script interpreter: ruby"
            ):
                package.check({}, "", deploydir)

    def test_package_check_rejects_non_fhs_executable_interpreter(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self.write_script(deploydir, "#!/usr/local/bin/python3")
            package = self.ScriptPackage(
                __file__, dependencies=("python3",)
            )
            with self.assertRaisesRegex(
                RuntimeError, "non-FHS executable script interpreter"
            ):
                package.check({}, "", deploydir)

    def test_package_check_ignores_documentation_examples(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self.write_script(
                deploydir,
                "#!/usr/bin/ruby",
                relative="usr/share/doc/example/sample",
            )
            package = self.ScriptPackage(__file__)
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
