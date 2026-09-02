import os
import unittest

from .package import GdbmPackage


class GdbmPackageTest(unittest.TestCase):
    def test_pedigree_timer_avoids_unavailable_getrusage(self):
        package = GdbmPackage(__file__)
        self.assertEqual(package.patches({}, ""), ["pedigree-timing.diff"])

        patch_path = os.path.join(
            os.path.dirname(__file__), "patches", "pedigree-timing.diff"
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        pedigree_branch = patch.split("+#ifdef __pedigree__", 1)[1]
        pedigree_branch = pedigree_branch.split("+#else", 1)[0]
        self.assertNotIn("getrusage", pedigree_branch)
        self.assertIn("t->have_rusage && timing_getrusage", patch)
        self.assertIn("t->user.tv_sec = t->user.tv_usec = 0", patch)
        self.assertIn("t->sys.tv_sec = t->sys.tv_usec = 0", patch)


if __name__ == "__main__":
    unittest.main()
