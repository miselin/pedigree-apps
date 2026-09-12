import hashlib
import io
import mmap
import os
import tarfile
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from . import install


class InstallPackageCommandTest(unittest.TestCase):
    def test_upgrade_preserves_open_executable_inode_and_mapping(self):
        archive_bytes, contents = self.archive()
        with tempfile.TemporaryDirectory() as temporary:
            target = os.path.join(temporary, "usr/share/example.txt")
            os.makedirs(os.path.dirname(target))
            old_contents = b"previous executable contents\n"
            with open(target, "wb") as previous:
                previous.write(old_contents)
            os.chmod(target, 0o755)
            with open(target, "rb") as running:
                with mmap.mmap(running.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
                    with install.InstallTarFile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
                        archive.extractall(temporary)
                    self.assertEqual(running.read(), old_contents)
                    self.assertEqual(mapped[:], old_contents)
                    self.assertNotEqual(os.fstat(running.fileno()).st_ino, os.stat(target).st_ino)
            with open(target, "rb") as installed:
                self.assertEqual(installed.read(), contents)
            self.assertEqual(os.stat(target).st_mode & 0o777, 0o644)

    def test_failed_replacement_keeps_previous_file_and_removes_temporary(self):
        archive_bytes, _ = self.archive()
        with tempfile.TemporaryDirectory() as temporary:
            target = os.path.join(temporary, "usr/share/example.txt")
            parent = os.path.dirname(target)
            os.makedirs(parent)
            with open(target, "wb") as previous:
                previous.write(b"previous contents")
            with install.InstallTarFile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
                with mock.patch.object(install.os, "replace", side_effect=OSError("disk error")):
                    with self.assertRaises(OSError):
                        archive.extractall(temporary)
            with open(target, "rb") as previous:
                self.assertEqual(previous.read(), b"previous contents")
            self.assertEqual(os.listdir(parent), ["example.txt"])

    def archive(self):
        output = io.BytesIO()
        contents = b"installed package\n"
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            member = tarfile.TarInfo("usr/share/example.txt")
            member.size = len(contents)
            archive.addfile(member, io.BytesIO(contents))
        return output.getvalue(), contents

    @staticmethod
    def package(name, digest, dependencies=None, architecture="amd64"):
        package = {
            "name": name,
            "version": "1.2",
            "architecture": architecture,
            "sha1": digest,
        }
        if dependencies is not None:
            package["dependencies"] = dependencies
        return package

    def configuration(self, temporary, digest, repositories, database=None):
        if database is None:
            database = {"example-amd64": self.package("example", digest)}
        return SimpleNamespace(
            architecture="amd64",
            db=database,
            install_root=os.path.join(temporary, "root"),
            local_cache=os.path.join(temporary, "cache"),
            repo_urls=repositories,
        )

    @staticmethod
    def arguments():
        return SimpleNamespace(package=["example"], nodeps=False)

    def test_digest_mismatch_is_unlinked_and_falls_back(self):
        valid_archive, installed_contents = self.archive()
        digest = hashlib.sha1(valid_archive).hexdigest()

        with tempfile.TemporaryDirectory() as temporary:
            config = self.configuration(
                temporary,
                digest,
                ["https://bad.example", "https://good.example"],
            )
            os.makedirs(config.local_cache)

            def download(url, target):
                target.write(
                    b"wrong archive"
                    if url.startswith("https://bad.example/")
                    else valid_archive
                )

            with (
                mock.patch.object(
                    install.pup_http, "copy_url", side_effect=download
                ) as copy_url,
                mock.patch("builtins.print"),
            ):
                result = install.InstallCommand().run(self.arguments(), config)

            package_path = os.path.join(
                config.local_cache, "example-1.2-amd64.pup"
            )
            self.assertIsNone(result)
            self.assertEqual(
                [call.args[0] for call in copy_url.call_args_list],
                [
                    "https://bad.example/example-1.2-amd64.pup",
                    "https://good.example/example-1.2-amd64.pup",
                ],
            )
            with open(package_path, "rb") as package:
                self.assertEqual(package.read(), valid_archive)
            with open(
                os.path.join(config.install_root, "usr", "share", "example.txt"),
                "rb",
            ) as installed:
                self.assertEqual(installed.read(), installed_contents)

    def test_digest_mismatch_without_fallback_leaves_no_archive(self):
        valid_archive, _ = self.archive()
        digest = hashlib.sha1(valid_archive).hexdigest()

        with tempfile.TemporaryDirectory() as temporary:
            config = self.configuration(
                temporary, digest, ["https://bad.example"]
            )
            os.makedirs(config.local_cache)
            package_path = os.path.join(
                config.local_cache, "example-1.2-amd64.pup"
            )

            with (
                mock.patch.object(
                    install.pup_http,
                    "copy_url",
                    side_effect=lambda url, target: target.write(b"wrong archive"),
                ),
                mock.patch("builtins.print"),
            ):
                result = install.InstallCommand().run(self.arguments(), config)

            self.assertEqual(result, 1)
            self.assertFalse(os.path.exists(package_path))
            self.assertFalse(
                os.path.exists(
                    os.path.join(
                        config.install_root, "usr", "share", "example.txt"
                    )
                )
            )

    def test_valid_download_stops_after_first_repository(self):
        valid_archive, installed_contents = self.archive()
        digest = hashlib.sha1(valid_archive).hexdigest()

        with tempfile.TemporaryDirectory() as temporary:
            config = self.configuration(
                temporary,
                digest,
                ["https://first.example", "https://unused.example"],
            )
            os.makedirs(config.local_cache)

            with (
                mock.patch.object(
                    install.pup_http,
                    "copy_url",
                    side_effect=lambda url, target: target.write(valid_archive),
                ) as copy_url,
                mock.patch("builtins.print"),
            ):
                result = install.InstallCommand().run(self.arguments(), config)

            self.assertIsNone(result)
            copy_url.assert_called_once()
            self.assertEqual(
                copy_url.call_args.args[0],
                "https://first.example/example-1.2-amd64.pup",
            )
            with open(
                os.path.join(config.install_root, "usr", "share", "example.txt"),
                "rb",
            ) as installed:
                self.assertEqual(installed.read(), installed_contents)

    def test_dependencies_are_installed_first_once_in_stable_order(self):
        valid_archive, _ = self.archive()
        digest = hashlib.sha1(valid_archive).hexdigest()
        database = {
            "shared-amd64": self.package("shared", digest),
            "middle-amd64": self.package("middle", digest, ["shared"]),
            "first-amd64": self.package("first", digest, ["middle"]),
            "second-amd64": self.package("second", digest, ["shared"]),
        }

        with tempfile.TemporaryDirectory() as temporary:
            config = self.configuration(
                temporary,
                digest,
                ["https://repo.example"],
                database,
            )
            os.makedirs(config.local_cache)

            with (
                mock.patch.object(
                    install.pup_http,
                    "copy_url",
                    side_effect=lambda url, target: target.write(valid_archive),
                ) as copy_url,
                mock.patch("builtins.print"),
            ):
                result = install.InstallCommand().run(
                    SimpleNamespace(
                        package=["first", "second"], nodeps=False
                    ),
                    config,
                )

            self.assertIsNone(result)
            self.assertEqual(
                [call.args[0] for call in copy_url.call_args_list],
                [
                    "https://repo.example/shared-1.2-amd64.pup",
                    "https://repo.example/middle-1.2-amd64.pup",
                    "https://repo.example/first-1.2-amd64.pup",
                    "https://repo.example/second-1.2-amd64.pup",
                ],
            )

    def test_missing_same_architecture_dependency_fails_before_download(self):
        valid_archive, _ = self.archive()
        digest = hashlib.sha1(valid_archive).hexdigest()
        database = {
            "example-amd64": self.package("example", digest, ["library"]),
            "library-arm64": self.package(
                "library", digest, architecture="arm64"
            ),
        }

        with tempfile.TemporaryDirectory() as temporary:
            config = self.configuration(
                temporary,
                digest,
                ["https://repo.example"],
                database,
            )
            os.makedirs(config.local_cache)

            with (
                mock.patch.object(install.pup_http, "copy_url") as copy_url,
                mock.patch("builtins.print") as print_message,
            ):
                result = install.InstallCommand().run(self.arguments(), config)

            self.assertEqual(result, 1)
            copy_url.assert_not_called()
            self.assertIn(
                'The dependency "library" required by "example" is not '
                'available for architecture "amd64".',
                str(print_message.call_args.args[0]),
            )

    def test_dependency_cycle_fails_before_download(self):
        valid_archive, _ = self.archive()
        digest = hashlib.sha1(valid_archive).hexdigest()
        database = {
            "first-amd64": self.package("first", digest, ["second"]),
            "second-amd64": self.package("second", digest, ["first"]),
        }

        with tempfile.TemporaryDirectory() as temporary:
            config = self.configuration(
                temporary,
                digest,
                ["https://repo.example"],
                database,
            )
            os.makedirs(config.local_cache)

            with (
                mock.patch.object(install.pup_http, "copy_url") as copy_url,
                mock.patch("builtins.print") as print_message,
            ):
                result = install.InstallCommand().run(
                    SimpleNamespace(package=["first"], nodeps=False), config
                )

            self.assertEqual(result, 1)
            copy_url.assert_not_called()
            self.assertEqual(
                str(print_message.call_args.args[0]),
                "Dependency cycle detected: first -> second -> first.",
            )

    def test_nodeps_keeps_legacy_root_only_install_behavior(self):
        valid_archive, _ = self.archive()
        digest = hashlib.sha1(valid_archive).hexdigest()
        database = {
            "example-amd64": self.package("example", digest, ["unavailable"]),
        }

        with tempfile.TemporaryDirectory() as temporary:
            config = self.configuration(
                temporary,
                digest,
                ["https://repo.example"],
                database,
            )
            os.makedirs(config.local_cache)

            with (
                mock.patch.object(
                    install.pup_http,
                    "copy_url",
                    side_effect=lambda url, target: target.write(valid_archive),
                ) as copy_url,
                mock.patch("builtins.print"),
            ):
                result = install.InstallCommand().run(
                    SimpleNamespace(package=["example"], nodeps=True), config
                )

            self.assertIsNone(result)
            copy_url.assert_called_once_with(
                "https://repo.example/example-1.2-amd64.pup", mock.ANY
            )


if __name__ == "__main__":
    unittest.main()
