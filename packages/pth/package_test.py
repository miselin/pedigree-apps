import unittest

from .package import DISABLED_REASON


class PthPackageTest(unittest.TestCase):
    def test_port_is_deferred_without_mandatory_signal_primitives(self):
        self.assertIn("sigpending()", DISABLED_REASON)
        self.assertIn("sigsuspend()", DISABLED_REASON)
        self.assertIn("no active port depends on Pth", DISABLED_REASON)


if __name__ == "__main__":
    unittest.main()
