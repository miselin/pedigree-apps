
import os
import tempfile
import unittest
from unittest import mock

import buildPackages
from support import buildsystem


class BuildPackagesTest(unittest.TestCase):
    class RuntimeDependentPackage(buildsystem.Package):
        def name(self):
            return "dependent"

        def version(self):
            return "1.0"

        def install_deps(self):
            return ["runtime"]

    class UploadablePackage(buildsystem.Package):
        def name(self):
            return "uploadable"

        def version(self):
            return "1.0"

    def test_inner_builder_refuses_a_key_during_builds(self):
        with mock.patch.dict(
            os.environ,
            {"PEDIGREE_APPS_CONTAINER": "1", "UPLOAD_KEY": "secret"},
            clear=False,
        ), mock.patch(
            "buildPackages.environment.generate_environment"
        ) as generate_environment:
            result = buildPackages.main(["buildPackages.py", "--only", "example"])

        self.assertEqual(result, 2)
        generate_environment.assert_not_called()

    def test_upload_only_never_starts_a_build(self):
        package = self.UploadablePackage(__file__)
        packages = {package.name(): package}
        ordered = [(package.name(), package)]
        build_env = {"SAFE": "value"}
        with mock.patch.dict(
            os.environ,
            {"PEDIGREE_APPS_CONTAINER": "1", "UPLOAD_KEY": "secret"},
            clear=False,
        ), mock.patch(
            "buildPackages.environment.generate_environment",
            return_value=build_env,
        ), mock.patch(
            "buildPackages.buildsystem.load_packages",
            return_value=packages,
        ), mock.patch(
            "buildPackages.deps.sort_dependencies",
            return_value=ordered,
        ), mock.patch(
            "buildPackages.steps.prepare_package_manager"
        ), mock.patch(
            "buildPackages.build_all",
        ) as build_all, mock.patch(
            "buildPackages.upload_all",
            return_value=0,
        ) as upload_all:
            result = buildPackages.main(
                [
                    "buildPackages.py",
                    "--only",
                    package.name(),
                    "--upload-only",
                ]
            )

        self.assertEqual(result, 0)
        build_all.assert_not_called()
        upload_all.assert_called_once_with(ordered, build_env, "secret")

    def test_upload_preflight_rejects_runtime_dependencies(self):
        package = self.RuntimeDependentPackage(__file__)
        packages = [(package.name(), package)]
        self.assertFalse(buildPackages.upload_metadata_supported(packages))

    def test_upload_only_requires_complete_artifacts(self):
        package = self.UploadablePackage(__file__)
        with tempfile.TemporaryDirectory() as temporary:
            env = {
                "OUTPUT_BASE": os.path.join(temporary, "output"),
                "PACKMAN_REPO": os.path.join(temporary, "repo"),
                "PACKMAN_TARGET_ARCH": "amd64",
            }
            with mock.patch.object(package, "repository") as repository:
                result = buildPackages.upload_all(
                    [(package.name(), package)], env, "secret"
                )
            self.assertEqual(result, 2)
            repository.assert_not_called()

    def test_upload_only_registers_complete_artifacts(self):
        package = self.UploadablePackage(__file__)
        with tempfile.TemporaryDirectory() as temporary:
            env = {
                "OUTPUT_BASE": os.path.join(temporary, "output"),
                "PACKMAN_REPO": os.path.join(temporary, "repo"),
                "PACKMAN_TARGET_ARCH": "amd64",
            }
            deploy_base = os.path.join(
                env["OUTPUT_BASE"], package.name(), package.version()
            )
            os.makedirs(os.path.join(deploy_base, "root"))
            os.makedirs(env["PACKMAN_REPO"])
            with open(
                os.path.join(deploy_base, ".complete"),
                "w",
                encoding="utf-8",
            ):
                pass
            with open(
                os.path.join(
                    env["PACKMAN_REPO"], "uploadable-1.0-amd64.pup"
                ),
                "w",
                encoding="utf-8",
            ):
                pass

            with mock.patch("buildPackages.steps.upload_package") as upload:
                result = buildPackages.upload_all(
                    [(package.name(), package)], env, "secret"
                )
            self.assertEqual(result, 0)
            upload.assert_called_once_with(
                package,
                os.path.join(deploy_base, "root"),
                env,
                "secret",
            )


if __name__ == '__main__':
    unittest.main()
