import ast
import os
import re
import tempfile
import unittest
from unittest import mock

import environment

from . import buildsystem
from . import deps


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.env = environment.generate_environment("amd64", recurse=False)
        repository = os.path.dirname(os.path.dirname(__file__))
        self.env["SOURCE_BASE"] = os.path.join(repository, "packages")
        self.packages = buildsystem.load_packages(self.env)

    def test_dependency_metadata_resolves(self):
        deps.sort_dependencies(self.packages)
        for package in self.packages.values():
            for dependency in package.install_deps():
                self.assertIn(
                    dependency,
                    self.packages,
                    "%s has unknown runtime dependency %s"
                    % (package.name(), dependency),
                )

    def test_base_runtime_packages_are_not_recipe_dependencies(self):
        self.assertEqual(
            buildsystem.BASE_RUNTIME_PACKAGES, ("bash", "coreutils")
        )
        for package in self.packages.values():
            unexpected = set(package.install_deps()).intersection(
                buildsystem.BASE_RUNTIME_PACKAGES
            )
            self.assertFalse(
                unexpected,
                "%s declares target base invariant as runtime dependency: %s"
                % (package.name(), ", ".join(sorted(unexpected))),
            )

    def test_tls_clients_include_system_trust_store(self):
        for name in ("cmake", "curl", "lynx", "python3", "wget"):
            package = self.packages[name]
            with self.subTest(package=name, dependency="build"):
                self.assertIn("ca-certificates", package.build_requires())
            with self.subTest(package=name, dependency="runtime"):
                self.assertIn("ca-certificates", package.install_deps())

    def test_versions_are_legacy_pup_orderable(self):
        for name, package in self.packages.items():
            with self.subTest(package=name):
                self.assertRegex(
                    package.version(),
                    r"^\d+(?:\.\d+)*$",
                    "legacy PUP versions must be dot-separated integers",
                )

    def test_downloaded_sources_use_https_and_sha256(self):
        calls = []

        def record_download(url, target, sha256=None):
            calls.append((url, sha256))

        with mock.patch("support.steps.download", side_effect=record_download):
            for package in self.packages.values():
                try:
                    package.download(self.env.copy(), "/tmp/catalog-source")
                except buildsystem.OptionalError:
                    continue

        for url, sha256 in calls:
            self.assertTrue(url.startswith("https://"), url)
            self.assertRegex(sha256 or "", re.compile(r"^[0-9a-f]{64}$"), url)

    def test_all_source_download_calls_are_pinned(self):
        checked = set()
        for package in self.packages.values():
            package_file = os.path.join(package._path, "package.py")
            if package_file in checked:
                continue
            checked.add(package_file)

            with open(package_file, encoding="utf-8") as source:
                contents = source.read()
            self.assertNotIn("http://", contents, package.name())

            tree = ast.parse(contents, filename=package_file)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                function = node.func
                if not (
                    isinstance(function, ast.Attribute)
                    and function.attr == "download"
                    and isinstance(function.value, ast.Name)
                    and function.value.id == "steps"
                ):
                    continue
                self.assertIn(
                    "sha256",
                    {keyword.arg for keyword in node.keywords},
                    "%s has an unpinned source download at line %d"
                    % (package.name(), node.lineno),
                )

    def test_declared_patches_exist(self):
        with tempfile.TemporaryDirectory() as source:
            for package in self.packages.values():
                try:
                    patches = package.patches(self.env.copy(), source)
                except buildsystem.OptionalError:
                    continue
                for patch in patches:
                    path = os.path.join(package._path, "patches", patch)
                    self.assertTrue(
                        os.path.isfile(path),
                        "%s declares missing patch %s"
                        % (package.name(), patch),
                    )


if __name__ == "__main__":
    unittest.main()
