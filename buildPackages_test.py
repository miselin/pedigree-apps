
import os
import subprocess
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

    class RuntimePackage(buildsystem.Package):
        def name(self):
            return "runtime"

        def version(self):
            return "1.0"

    def test_wrapper_accepts_no_package_arguments(self):
        repository = os.path.dirname(__file__)
        with tempfile.TemporaryDirectory() as temporary:
            docker = os.path.join(temporary, "docker")
            docker_log = os.path.join(temporary, "docker.log")
            with open(docker, "w", encoding="utf-8") as executable:
                executable.write(
                    "#!/bin/sh\n"
                    'printf "%s\\n" "$*" >> "$DOCKER_LOG"\n'
                )
            os.chmod(docker, 0o755)

            command_env = os.environ.copy()
            command_env.pop("UPLOAD_KEY", None)
            command_env.update(
                {
                    "DOCKER_LOG": docker_log,
                    "PATH": temporary + os.pathsep + command_env["PATH"],
                    "PEDIGREE_APPS_BUILDER_IMAGE": "wrapper-test",
                }
            )
            result = subprocess.run(
                [os.path.join(repository, "buildPackages.sh")],
                cwd=repository,
                env=command_env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            with open(docker_log, encoding="utf-8") as invocation_log:
                invocations = invocation_log.read()
            self.assertIn("image inspect wrapper-test", invocations)
            self.assertIn("python3 /workspace/buildPackages.py --target amd64", invocations)

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

    def test_audit_only_never_prepares_or_builds(self):
        package = self.UploadablePackage(__file__)
        packages = {package.name(): package}
        ordered = [(package.name(), package)]
        build_env = {"SAFE": "value"}
        with mock.patch.dict(
            os.environ,
            {"PEDIGREE_APPS_CONTAINER": "1"},
            clear=True,
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
        ) as prepare_package_manager, mock.patch(
            "buildPackages.build_all"
        ) as build_all, mock.patch(
            "buildPackages.audit.audit_packages",
            return_value=0,
        ) as audit_packages:
            result = buildPackages.main(["buildPackages.py", "--audit-only"])

        self.assertEqual(result, 0)
        prepare_package_manager.assert_not_called()
        build_all.assert_not_called()
        audit_packages.assert_called_once_with(ordered, build_env)

    def test_upload_order_follows_runtime_dependencies(self):
        package = self.RuntimeDependentPackage(__file__)
        runtime = self.RuntimePackage(__file__)
        packages = [(package.name(), package), (runtime.name(), runtime)]

        ordered = buildPackages.order_uploads(packages)

        self.assertEqual([name for name, _ in ordered], ["runtime", "dependent"])

    def test_upload_only_registers_in_runtime_dependency_order(self):
        package = self.RuntimeDependentPackage(__file__)
        runtime = self.RuntimePackage(__file__)
        with tempfile.TemporaryDirectory() as temporary:
            env = {
                "OUTPUT_BASE": os.path.join(temporary, "output"),
                "PACKMAN_REPO": os.path.join(temporary, "repo"),
                "PACKMAN_TARGET_ARCH": "amd64",
            }
            os.makedirs(env["PACKMAN_REPO"])
            for current in (package, runtime):
                deploy_base = os.path.join(
                    env["OUTPUT_BASE"], current.name(), current.version()
                )
                os.makedirs(os.path.join(deploy_base, "root"))
                with open(os.path.join(deploy_base, ".complete"), "w"):
                    pass
                with open(
                    os.path.join(
                        env["PACKMAN_REPO"],
                        "%s-%s-amd64.pup"
                        % (current.name(), current.version()),
                    ),
                    "wb",
                ):
                    pass

            uploaded = []
            with mock.patch(
                "buildPackages.steps.upload_package",
                side_effect=lambda current, *unused: uploaded.append(
                    current.name()
                ),
            ):
                result = buildPackages.upload_all(
                    [(package.name(), package), (runtime.name(), runtime)],
                    env,
                    "secret",
                )

        self.assertEqual(result, 0)
        self.assertEqual(uploaded, ["runtime", "dependent"])

    def test_upload_only_stops_on_first_registration_failure(self):
        first = self.RuntimePackage(__file__)
        second = self.UploadablePackage(__file__)
        with tempfile.TemporaryDirectory() as temporary:
            env = {
                "OUTPUT_BASE": os.path.join(temporary, "output"),
                "PACKMAN_REPO": os.path.join(temporary, "repo"),
                "PACKMAN_TARGET_ARCH": "amd64",
            }
            os.makedirs(env["PACKMAN_REPO"])
            for current in (first, second):
                deploy_base = os.path.join(
                    env["OUTPUT_BASE"], current.name(), current.version()
                )
                os.makedirs(os.path.join(deploy_base, "root"))
                with open(os.path.join(deploy_base, ".complete"), "w"):
                    pass
                with open(
                    os.path.join(
                        env["PACKMAN_REPO"],
                        "%s-%s-amd64.pup"
                        % (current.name(), current.version()),
                    ),
                    "wb",
                ):
                    pass

            with mock.patch(
                "buildPackages.steps.upload_package",
                side_effect=RuntimeError("verification failed"),
            ) as upload:
                result = buildPackages.upload_all(
                    [(first.name(), first), (second.name(), second)],
                    env,
                    "secret",
                )

        self.assertEqual(result, 1)
        self.assertEqual(upload.call_count, 1)

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
