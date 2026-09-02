import pathlib
import tempfile
import unittest

from .package import PupPackage


class PupPackageTest(unittest.TestCase):
    def test_runtime_contract_covers_python_and_https_trust(self):
        package = PupPackage(__file__)

        self.assertEqual(
            package.build_requires(), ["ca-certificates", "python3"]
        )
        self.assertEqual(package.install_deps(), package.build_requires())

    def test_deploy_installs_python3_client_under_fhs_paths(self):
        repository = pathlib.Path(__file__).resolve().parents[2]
        package = PupPackage(__file__)

        with tempfile.TemporaryDirectory() as deploydir:
            package.deploy(
                {"APPS_BASE": str(repository)},
                "/unused",
                deploydir,
            )

            launcher = pathlib.Path(deploydir, "usr", "bin", "pup")
            config = pathlib.Path(deploydir, "etc", "pup", "pup.conf")
            installed_package = pathlib.Path(
                deploydir,
                "usr",
                "lib",
                "python3.14",
                "site-packages",
                "pedigree_updater",
            )

            self.assertEqual(
                launcher.read_text(encoding="utf-8").splitlines()[0],
                "#!/usr/bin/python3",
            )
            self.assertEqual(launcher.stat().st_mode & 0o777, 0o755)
            self.assertTrue(
                (installed_package / "commands" / "install.py").is_file()
            )
            self.assertFalse(
                any(installed_package.rglob("__pycache__"))
            )
            self.assertFalse(any(installed_package.rglob("*.pyc")))
            self.assertFalse(any(installed_package.rglob("*_test.py")))
            self.assertTrue(
                pathlib.Path(deploydir, "var", "lib", "pup").is_dir()
            )

            config_contents = config.read_text(encoding="utf-8")
            self.assertIn("localdb=/var/lib/pup", config_contents)
            self.assertIn(
                "server=https://pup.pedigree-project.org",
                config_contents,
            )
            self.assertNotIn("/support", config_contents)
            package.check(
                {"APPS_BASE": str(repository)},
                "/unused",
                deploydir,
            )

    def test_configuration_examples_use_target_fhs_and_https(self):
        repository = pathlib.Path(__file__).resolve().parents[2]
        examples = (
            repository / "pup" / "pup.conf.default",
            repository
            / "pup"
            / "http"
            / "pup_http"
            / "resources"
            / "static"
            / "pup.conf",
            repository
            / "pup"
            / "http"
            / "pup_http"
            / "templates"
            / "index.html",
        )
        for example in examples:
            with self.subTest(example=example):
                contents = example.read_text(encoding="utf-8")
                self.assertNotIn("/support/pup", contents)
                self.assertNotIn("http://", contents)
                self.assertIn("/var/lib/pup", contents)
                self.assertIn(
                    "https://pup.pedigree-project.org",
                    contents,
                )

    def test_target_client_has_no_third_party_http_import(self):
        repository = pathlib.Path(__file__).resolve().parents[2]
        client = repository / "pup" / "pedigree_updater"
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in client.rglob("*.py")
        )

        self.assertNotIn("import requests", sources)
        self.assertNotIn("from requests", sources)
        project_metadata = (
            repository / "pup" / "pyproject.toml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("requests", project_metadata.lower())
        self.assertIn("dependencies = []", project_metadata)


if __name__ == "__main__":
    unittest.main()
