import hashlib
import io
import os
import tarfile
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from . import install


class InstallPackageCommandTest(unittest.TestCase):
    def archive(self):
        output = io.BytesIO()
        contents = b"installed package\n"
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            member = tarfile.TarInfo("usr/share/example.txt")
            member.size = len(contents)
            archive.addfile(member, io.BytesIO(contents))
        return output.getvalue(), contents

    def configuration(self, temporary, digest, repositories):
        return SimpleNamespace(
            architecture="amd64",
            db={
                "example-amd64": {
                    "name": "example",
                    "version": "1.2",
                    "architecture": "amd64",
                    "sha1": digest,
                }
            },
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


if __name__ == "__main__":
    unittest.main()
