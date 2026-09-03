import hashlib
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from . import register


class RegisterPackageCommandTest(unittest.TestCase):
    def test_registration_preserves_legacy_upload_fields(self):
        with tempfile.TemporaryDirectory() as cache:
            package_file = os.path.join(cache, "example-1.2-amd64.pup")
            contents = b"legacy pup contents"
            with open(package_file, "wb") as package:
                package.write(contents)

            args = SimpleNamespace(
                package="example",
                version="1.2",
                architecture="amd64",
                key="secret",
                dependency=["runtime", "runtime"],
            )
            config = SimpleNamespace(
                local_cache=cache,
                upload_url="https://repo.example",
            )
            with (
                mock.patch.object(
                    register.pup_http,
                    "get_text",
                    side_effect=(
                        json.dumps({"package_dependencies": 1}),
                        "https://upload.example/blobstore\n",
                        json.dumps(
                            {
                                "example-amd64": {
                                    "name": "example",
                                    "version": "1.2",
                                    "architecture": "amd64",
                                    "sha1": hashlib.sha1(contents).hexdigest(),
                                    "dependencies": ["runtime"],
                                }
                            }
                        ),
                    ),
                ) as get_text,
                mock.patch.object(
                    register.pup_http,
                    "post_multipart",
                    return_value="ok\n",
                ) as post_multipart,
                mock.patch.object(
                    register.pup_http,
                    "copy_url",
                    side_effect=lambda url, target, timeout: target.write(contents),
                ) as copy_url,
                mock.patch("builtins.print"),
            ):
                result = register.RegisterPackageCommand().run(args, config)

        self.assertIsNone(result)
        self.assertEqual(
            get_text.call_args_list,
            [
                mock.call(
                    "https://repo.example/capabilities.json", timeout=30
                ),
                mock.call(
                    "https://repo.example/upload",
                    parameters={"key": "upload", "key_value": "secret"},
                    timeout=30,
                ),
                mock.call(
                    "https://repo.example/packages.pupdb", timeout=30
                ),
            ],
        )
        post_multipart.assert_called_once_with(
            "https://upload.example/blobstore",
            {
                "name": "example",
                "vers": "1.2",
                "arch": "amd64",
                "sha1": hashlib.sha1(contents).hexdigest(),
                "dependencies": '["runtime"]',
            },
            "file",
            package_file,
            timeout=300,
        )
        copy_url.assert_called_once_with(
            "https://repo.example/example-1.2-amd64.pup",
            mock.ANY,
            timeout=300,
        )

    def test_unsupported_repository_is_rejected_before_requesting_upload_url(self):
        with tempfile.TemporaryDirectory() as cache:
            package_file = os.path.join(cache, "example-1.2-amd64.pup")
            with open(package_file, "wb") as package:
                package.write(b"contents")

            args = SimpleNamespace(
                package="example",
                version="1.2",
                architecture="amd64",
                key="secret",
                dependency=["runtime"],
            )
            config = SimpleNamespace(
                local_cache=cache,
                upload_url="https://repo.example",
            )
            with (
                mock.patch.object(
                    register.pup_http,
                    "get_text",
                    return_value=json.dumps({"package_database": 1}),
                ) as get_text,
                mock.patch.object(
                    register.pup_http, "post_multipart"
                ) as post_multipart,
                mock.patch("builtins.print"),
            ):
                result = register.RegisterPackageCommand().run(args, config)

        self.assertEqual(result, 1)
        get_text.assert_called_once_with(
            "https://repo.example/capabilities.json", timeout=30
        )
        post_multipart.assert_not_called()

    def test_verification_retries_and_reports_uploaded_but_unverified(self):
        with tempfile.TemporaryDirectory() as cache:
            package_file = os.path.join(cache, "example-1.2-amd64.pup")
            with open(package_file, "wb") as package:
                package.write(b"contents")

            args = SimpleNamespace(
                package="example",
                version="1.2",
                architecture="amd64",
                key="secret",
                dependency=[],
            )
            config = SimpleNamespace(
                local_cache=cache,
                upload_url="https://repo.example",
            )
            with (
                mock.patch.object(
                    register.pup_http,
                    "get_text",
                    side_effect=(
                        json.dumps({"package_dependencies": 1}),
                        "https://upload.example/blobstore\n",
                        "{}",
                        "{}",
                    ),
                ) as get_text,
                mock.patch.object(
                    register.pup_http,
                    "post_multipart",
                    return_value="ok\n",
                ) as post_multipart,
                mock.patch.object(register, "VERIFY_ATTEMPTS", 2),
                mock.patch.object(register.time, "sleep") as sleep,
                mock.patch("builtins.print") as output,
            ):
                result = register.RegisterPackageCommand().run(args, config)

        self.assertEqual(result, 1)
        post_multipart.assert_called_once()
        self.assertEqual(get_text.call_count, 4)
        sleep.assert_called_once_with(register.VERIFY_DELAY_SECONDS)
        self.assertIn("was uploaded", output.call_args.args[0])
        self.assertIn("verification failed", output.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
