import os
import tempfile
import unittest
from unittest import mock

from .package import DialogPackage


class DialogPackageTest(unittest.TestCase):
    @mock.patch('packages.dialog.package.steps.run_configure')
    def test_configure_omits_unsupported_docdir(self, run_configure):
        env = {}
        DialogPackage(__file__).configure(env, '/source')

        self.assertEqual(env['LIBS'], '-ltinfow')
        self.assertEqual(
            run_configure.call_args.kwargs['not_paths'], ('docdir',))
        extra_config = run_configure.call_args.kwargs['extra_config']
        self.assertIn(
            '--with-pkg-config-libdir=/usr/lib/pkgconfig', extra_config)
        self.assertIn('--with-ncursesw', extra_config)
        self.assertIn('--with-shared', extra_config)

    def test_postdeploy_sanitizes_installed_metadata(self):
        with tempfile.TemporaryDirectory() as deploydir:
            bindir = os.path.join(deploydir, 'usr', 'bin')
            pkgconfig_dir = os.path.join(
                deploydir, 'usr', 'lib', 'pkgconfig')
            os.makedirs(bindir)
            os.makedirs(pkgconfig_dir)

            env = {
                'APPS_BASE': '/workspace',
                'CROSS_BASE': '/opt/pedigree',
                'PORTS_SYSROOT': (
                    '/workspace/.build/x86_64/sysroots/dialog'),
                'TARGET_SYSROOT': '/opt/pedigree/x86_64-pedigree',
            }
            metadata_paths = (
                os.path.join(bindir, 'dialog-config'),
                os.path.join(pkgconfig_dir, 'dialog.pc'),
            )
            for metadata_path in metadata_paths:
                with open(metadata_path, 'w', encoding='utf-8') as metadata:
                    metadata.write(
                        'Cflags: -I%s/usr/include\n'
                        'Libs: -L%s/usr/lib -Wl,-rpath-link,%s/usr/lib '
                        '-ldialog\n'
                        % (
                            env['PORTS_SYSROOT'],
                            env['PORTS_SYSROOT'],
                            env['PORTS_SYSROOT'],
                        )
                    )

            DialogPackage(__file__).postdeploy(env, '', deploydir)

            for metadata_path in metadata_paths:
                with open(metadata_path, encoding='utf-8') as metadata:
                    contents = metadata.read()
                self.assertIn('-I/usr/include', contents)
                self.assertIn('-L/usr/lib', contents)
                self.assertNotIn('rpath-link', contents)
                self.assertNotIn(env['PORTS_SYSROOT'], contents)

    @mock.patch('packages.dialog.package.steps.make')
    def test_deploy_installs_library_development_files(self, make):
        DialogPackage(__file__).deploy({}, '/source', '/stage')

        self.assertEqual(
            [call.kwargs['target'] for call in make.call_args_list],
            ['install.libs', 'install-full'],
        )
        for call in make.call_args_list:
            self.assertIn('DESTDIR=/stage', call.kwargs['extra_opts'])


if __name__ == '__main__':
    unittest.main()
