import os
import tempfile
import unittest
from unittest import mock

from .package import BUILD_TARGETS
from .package import MANPAGES
from .package import OpenSshClientPackage
from .package import PROGRAMS


class OpenSshClientPackageTest(unittest.TestCase):

    def setUp(self):
        self.package = OpenSshClientPackage(__file__)

    def test_uses_the_full_client_crypto_runtime(self):
        self.assertEqual(self.package.name(), 'openssh-client')
        self.assertEqual(self.package.version(), '10.5.1')
        self.assertEqual(self.package.build_requires(), ['openssl', 'zlib'])
        self.assertEqual(self.package.install_deps(), ['openssl', 'zlib'])

    @mock.patch('packages.openssh_client.package.steps.download')
    def test_download_pins_portable_openssh_source(self, download):
        self.package.download({}, '/archive')

        self.assertEqual(
            download.call_args.args[0],
            'https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/'
            'openssh-10.5p1.tar.gz',
        )
        self.assertEqual(
            download.call_args.kwargs['sha256'],
            'd44d28a839ea9daf969cc69150fde59910b2b39361dad81a3bd6cbd19218db11',
        )

    @mock.patch('packages.openssh_client.package.steps.run_configure')
    def test_configure_enables_crypto_and_omits_unavailable_helpers(
        self, run_configure
    ):
        self.package.configure({}, '/source')

        options = run_configure.call_args.kwargs['extra_config']
        self.assertNotIn('--without-openssl', options)
        for option in (
            '--with-zlib',
            '--with-sandbox=no',
            '--disable-pkcs11',
            '--disable-security-key',
        ):
            self.assertIn(option, options)

    @mock.patch('packages.openssh_client.package.steps.make')
    def test_builds_only_client_programs_and_their_data(self, make):
        self.package.build({}, '/source')

        make.assert_called_once_with('/source', {}, extra_opts=BUILD_TARGETS)
        for server in ('sshd', 'sshd-auth', 'sshd-session', 'sftp-server'):
            self.assertNotIn(server, BUILD_TARGETS)

    def test_deploys_no_server_or_privileged_helper(self):
        with tempfile.TemporaryDirectory() as srcdir:
            with tempfile.TemporaryDirectory() as deploydir:
                sources = set(PROGRAMS)
                sources.update(source for source, _ in MANPAGES)
                sources.update(('ssh_config.out', 'LICENCE'))
                for name in sources:
                    with open(os.path.join(srcdir, name), 'w') as output:
                        output.write(name)

                self.package.deploy({}, srcdir, deploydir)

                files = []
                for current, _, names in os.walk(deploydir):
                    for name in names:
                        files.append(
                            os.path.relpath(os.path.join(current, name), deploydir)
                        )
                self.assertIn('usr/bin/ssh', files)
                self.assertIn('usr/bin/scp', files)
                self.assertIn('usr/bin/sftp', files)
                self.assertIn('etc/ssh/ssh_config', files)
                self.assertNotIn('usr/sbin/sshd', files)
                self.assertNotIn('usr/libexec/sftp-server', files)
                self.assertNotIn('usr/libexec/ssh-keysign', files)

if __name__ == '__main__':
    unittest.main()
