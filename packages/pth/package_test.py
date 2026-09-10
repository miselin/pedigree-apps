import unittest

from .package import DISABLED_REASON, UPSTREAM_VERSION


class PthPackageTest(unittest.TestCase):
    def test_port_is_deferred_without_an_active_consumer(self):
        self.assertEqual(UPSTREAM_VERSION, "2.0.7")
        self.assertIn("No active port", DISABLED_REASON)


if __name__ == "__main__":
    unittest.main()
