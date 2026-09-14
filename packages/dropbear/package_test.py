import unittest
from unittest import mock

from .package import DropbearPackage


class DropbearPackageTest(unittest.TestCase):

    def setUp(self):
        self.package = DropbearPackage(__file__)

    def test_release_version_has_numeric_pedigree_revision(self):
        self.assertEqual(self.package.version(), '2026.94')
        self.assertEqual(self.package.release_version(), '2026.94.1')

    @mock.patch('packages.dropbear.package.steps.run_configure')
    def test_configure_uses_openpty_but_disables_stub_accounting(
        self, run_configure
    ):
        self.package.configure({}, '/source')

        options = run_configure.call_args.kwargs['extra_config']
        self.assertNotIn('--disable-openpty', options)
        for option in (
            '--disable-lastlog',
            '--disable-utmp',
            '--disable-utmpx',
            '--disable-wtmp',
            '--disable-wtmpx',
            '--disable-loginfunc',
            '--disable-pututline',
            '--disable-pututxline',
        ):
            self.assertIn(option, options)


if __name__ == '__main__':
    unittest.main()
