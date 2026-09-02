import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from . import util


class UtilTest(unittest.TestCase):
    def test_missing_paths_section_uses_fhs_defaults(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = os.path.join(temporary, "pup.conf")
            with open(config_path, "w", encoding="utf-8") as config:
                config.write("[settings]\narch=amd64\n")

            with mock.patch.object(util, "PupConfig") as pup_config:
                util.load_config(SimpleNamespace(config=config_path))

        pup_config.assert_called_once_with(
            [],
            util.DEFAULT_LOCAL_CACHE,
            "/",
            "amd64",
            "",
        )


if __name__ == "__main__":
    unittest.main()
