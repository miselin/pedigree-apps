import os
import tempfile
import unittest
from unittest import mock

from support import steps

from .package import AprUtilPackage


class AprUtilPackageTest(unittest.TestCase):
    def setUp(self):
        self.package = AprUtilPackage(__file__)

    def test_current_release_and_dependencies(self):
        self.assertEqual(self.package.version(), '1.6.5')
        self.assertEqual(self.package.build_requires(), ['apr', 'expat'])
        self.assertEqual(
            self.package.install_deps(), ['apr', 'expat', 'sed']
        )
        self.assertEqual(
            self.package.patches({}, ''), ['cross-config-script.diff']
        )

    @mock.patch.object(steps, 'run_configure')
    def test_configure_uses_staged_apr_and_minimal_backends(
        self, run_configure
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            sysroot = os.path.join(tempdir, 'sysroot')
            source = os.path.join(tempdir, 'source')
            libtool_dir = os.path.join(
                sysroot, 'usr', 'share', 'apr-1', 'build'
            )
            os.makedirs(libtool_dir)
            os.makedirs(source)
            with open(
                os.path.join(libtool_dir, 'libtool'),
                'w',
                encoding='utf-8',
            ) as libtool:
                libtool.write(
                    'lt_sysroot=\n'
                    'hardcode_into_libs=yes\n'
                    'hardcode_libdir_flag_spec="\\$wl-rpath '
                    '\\$wl\\$libdir"\n'
                    'hardcode_action=immediate\n'
                )

            self.package.configure({'PORTS_SYSROOT': sysroot}, source)

        options = run_configure.call_args.kwargs['extra_config']
        self.assertIn(
            '--with-apr=%s/usr/bin/apr-1-config' % sysroot, options
        )
        self.assertIn('--with-expat=%s/usr' % sysroot, options)
        self.assertIn('--with-dbm=sdbm', options)
        self.assertIn('--includedir=/usr/include/apr-1', options)
        self.assertIn('--disable-util-dso', options)
        self.assertIn('--without-ldap', options)
        self.assertIn('--without-sqlite3', options)

    def test_make_uses_staged_apr_build_tools(self):
        with tempfile.TemporaryDirectory() as source:
            options = self.package._make_options(
                {
                    'PORTS_SYSROOT': '/sysroot',
                    'CROSS_CC': '/cross/bin/x86_64-pedigree-gcc',
                    'CROSS_CPP': '/cross/bin/x86_64-pedigree-cpp',
                    'CPPFLAGS': '-I/sysroot/usr/include',
                    'LDFLAGS': '-L/sysroot/usr/lib',
                },
                source,
            )

        self.assertIn(
            'apr_builders=/sysroot/usr/share/apr-1/build', options
        )
        self.assertTrue(
            any(option.startswith('LIBTOOL=/bin/sh ') for option in options)
        )
        self.assertIn('CC=/cross/bin/x86_64-pedigree-gcc', options)
        self.assertIn('CPPFLAGS=-I/sysroot/usr/include', options)

    @mock.patch.object(steps, 'download')
    def test_download_is_official_and_pinned(self, download):
        self.package.download({}, '/archive')

        url, target = download.call_args.args
        self.assertEqual(
            url,
            'https://downloads.apache.org/apr/apr-util-1.6.5.tar.bz2',
        )
        self.assertEqual(target, '/archive')
        self.assertRegex(
            download.call_args.kwargs['sha256'], r'^[0-9a-f]{64}$'
        )

    def test_postdeploy_keeps_libtool_dependencies_sysroot_relocatable(self):
        with tempfile.TemporaryDirectory() as deploydir:
            libdir = os.path.join(deploydir, 'usr', 'lib')
            os.makedirs(libdir)
            bindir = os.path.join(deploydir, 'usr', 'bin')
            os.makedirs(bindir)
            metadata = os.path.join(libdir, 'libaprutil-1.la')
            with open(metadata, 'w', encoding='utf-8') as archive:
                archive.write(
                    "dependency_libs=' -L/sysroot/usr/lib "
                    "/sysroot/usr/lib/libexpat.la "
                    "/sysroot//usr/lib/libapr-1.la'\n"
                    "libdir='/usr/lib'\n"
                )
            config_script = os.path.join(bindir, 'apu-1-config')
            with open(config_script, 'w', encoding='utf-8') as script:
                script.write(
                    '#!/bin/sh\n'
                    'root=${0%/usr/bin/apu-1-config}\n'
                    'case "$1" in\n'
                    '  --bindir) echo /usr/bin ;;\n'
                    '  --includedir) echo "$root/usr/include/apr-1" ;;\n'
                    '  --includes) echo "-I$root/usr/include/apr-1 '
                    '-I$root/usr/include" ;;\n'
                    '  --ldflags) echo "-L$root/usr/lib" ;;\n'
                    '  --link-ld) echo "-L$root/usr/lib -laprutil-1" ;;\n'
                    '  --link-libtool) echo "$root/usr/lib/'
                    'libaprutil-1.la" ;;\n'
                    'esac\n'
                )
            os.chmod(config_script, 0o755)

            with mock.patch.object(
                steps, 'get_builddir', return_value='/build/root'
            ):
                self.package.postdeploy(
                    {'PORTS_SYSROOT': '/sysroot'}, '/source', deploydir
                )

            with open(metadata, encoding='utf-8') as archive:
                contents = archive.read()
            self.assertIn(
                "dependency_libs=' -L=/usr/lib "
                "=/usr/lib/libexpat.la =/usr/lib/libapr-1.la'",
                contents,
            )
            self.assertIn("libdir='/usr/lib'", contents)

    def test_cross_config_patch_rebases_all_consumed_paths(self):
        patch_path = os.path.join(
            os.path.dirname(__file__),
            'patches',
            'cross-config-script.diff',
        )
        with open(patch_path, encoding='utf-8') as patch:
            contents = patch.read()
        for marker in (
            'location=crosscompile',
            'APU_TARGET_DIR=',
            '-I$APU_TARGET_DIR',
            '-L$APU_TARGET_DIR',
            '-R$APU_TARGET_DIR',
            'LA_FILE="$APU_TARGET_DIR$libdir/',
        ):
            self.assertIn(marker, contents)


if __name__ == '__main__':
    unittest.main()
