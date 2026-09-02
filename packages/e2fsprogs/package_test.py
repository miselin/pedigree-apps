import os
import unittest

from .package import e2fsprogsPackage


class E2fsprogsPackageTest(unittest.TestCase):
    def test_positional_io_fallback_is_registered(self):
        package = e2fsprogsPackage(__file__)
        self.assertEqual(package.patches({}, ""), ["pedigree-io.diff"])

        patch_path = os.path.join(
            os.path.dirname(__file__), "patches", "pedigree-io.diff"
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn("#ifndef HAVE_PREAD", patch)
        self.assertIn("#ifndef HAVE_PWRITE", patch)
        self.assertIn("current_offset = lseek(fd, 0, SEEK_CUR)", patch)
        self.assertIn(
            "defined(POSIX_FADV_WILLNEED) && "
            "defined(HAVE_POSIX_FADVISE)",
            patch,
        )


if __name__ == "__main__":
    unittest.main()
