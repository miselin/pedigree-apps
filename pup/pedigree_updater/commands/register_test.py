import hashlib
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
                    return_value="https://upload.example/blobstore\n",
                ) as get_text,
                mock.patch.object(
                    register.pup_http,
                    "post_multipart",
                    return_value="ok\n",
                ) as post_multipart,
                mock.patch("builtins.print"),
            ):
                result = register.RegisterPackageCommand().run(args, config)

        self.assertIsNone(result)
        get_text.assert_called_once_with(
            "https://repo.example/upload",
            parameters={"key": "upload", "key_value": "secret"},
            timeout=30,
        )
        post_multipart.assert_called_once_with(
            "https://upload.example/blobstore",
            {
                "name": "example",
                "vers": "1.2",
                "arch": "amd64",
                "sha1": hashlib.sha1(contents).hexdigest(),
            },
            "file",
            package_file,
            timeout=300,
        )


if __name__ == "__main__":
    unittest.main()
