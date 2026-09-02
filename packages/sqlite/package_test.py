import os
import unittest

from .package import Sqlite


class SqlitePackageTest(unittest.TestCase):
    def test_cli_uses_supported_pedigree_timing_and_trap_paths(self):
        package = Sqlite(__file__)
        self.assertEqual(
            package.patches({}, ""), ["pedigree-cli-syscalls.diff"]
        )

        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "pedigree-cli-syscalls.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn("#elif defined(__pedigree__)", patch)
        self.assertIn("getrusage(A,B) memset(B,0,sizeof(*B))", patch)
        self.assertIn("kill(GETPID(), SIGTRAP)", patch)


if __name__ == "__main__":
    unittest.main()
