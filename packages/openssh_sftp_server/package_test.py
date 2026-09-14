import os
import tempfile
import unittest
from unittest import mock

from .package import OpenSshSftpServerPackage


class OpenSshSftpServerPackageTest(unittest.TestCase):

    def setUp(self):
        self.package = OpenSshSftpServerPackage(__file__)

    def test_is_a_standalone_dropbear_companion(self):
        self.assertEqual(self.package.name(), 'openssh-sftp-server')
        self.assertEqual(self.package.version(), '10.5.1')
        self.assertEqual(self.package.build_requires(), [])
        self.assertEqual(self.package.install_deps(), [])

    @mock.patch('packages.openssh_sftp_server.package.steps.download')
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

    @mock.patch('packages.openssh_sftp_server.package.steps.run_configure')
    def test_configure_keeps_the_helper_dependency_free(self, run_configure):
        self.package.configure({}, '/source')

        options = run_configure.call_args.kwargs['extra_config']
        for option in (
            '--libexecdir=/usr/libexec',
            '--without-openssl',
            '--without-zlib',
            '--with-sandbox=no',
            '--disable-security-key',
        ):
            self.assertIn(option, options)

    @mock.patch('packages.openssh_sftp_server.package.steps.make')
    def test_builds_only_sftp_server(self, make):
        self.package.build({}, '/source')

        make.assert_called_once_with('/source', {}, target='sftp-server')

    def test_deploys_only_the_server_manpage_and_licence(self):
        with tempfile.TemporaryDirectory() as srcdir:
            with tempfile.TemporaryDirectory() as deploydir:
                for name in ('sftp-server', 'sftp-server.8', 'LICENCE'):
                    with open(os.path.join(srcdir, name), 'w') as output:
                        output.write(name)

                self.package.deploy({}, srcdir, deploydir)

                files = []
                for current, _, names in os.walk(deploydir):
                    for name in names:
                        files.append(
                            os.path.relpath(os.path.join(current, name), deploydir)
                        )
                self.assertEqual(
                    sorted(files),
                    [
                        'usr/libexec/sftp-server',
                        'usr/share/doc/openssh-sftp-server/LICENCE',
                        'usr/share/man/man8/sftp-server.8',
                    ],
                )


if __name__ == '__main__':
    unittest.main()
