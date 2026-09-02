import io
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from . import dist


class DistTest(unittest.TestCase):
    def test_upload_key_from_datastore(self):
        response = io.BytesIO(
            json.dumps(
                {
                    "batch": {
                        "entityResults": [
                            {
                                "entity": {
                                    "properties": {
                                        "allowed": {"booleanValue": True},
                                        "key_value": {"stringValue": "secret"},
                                    }
                                }
                            }
                        ]
                    }
                }
            ).encode("utf-8")
        )
        with mock.patch(
            "pup.dist.subprocess.run",
            return_value=SimpleNamespace(stdout="token\n"),
        ), mock.patch("pup.dist.urlopen", return_value=response):
            self.assertEqual(
                dist.upload_key_from_datastore("example-project"), "secret"
            )


if __name__ == "__main__":
    unittest.main()
