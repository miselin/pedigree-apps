import unittest
from unittest import mock

from .package import DropbearPackage, PROGRAMS


class DropbearPackageTest(unittest.TestCase):

    def setUp(self):
        self.package = DropbearPackage(__file__)

    def test_release_version_has_numeric_pedigree_revision(self):
        self.assertEqual(self.package.version(), '2026.94')
        self.assertEqual(self.package.release_version(), '2026.94.3')

    def test_runtime_includes_the_sftp_server(self):
        self.assertEqual(
            self.package.install_deps(), ['zlib', 'openssh-sftp-server']
        )

    def test_scp_is_owned_by_openssh_client(self):
        self.assertNotIn(' scp', PROGRAMS)

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
