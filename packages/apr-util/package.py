import os
import re
import subprocess

from support import buildsystem
from support import steps


class AprUtilPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(AprUtilPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'bz2'

    def name(self):
        return 'apr-util'

    def version(self):
        return '1.6.5'

    def build_requires(self):
        return ['apr', 'expat']

    def install_deps(self):
        # apu-1-config uses sed to parse command-line assignments.
        return self.build_requires() + ['sed']

    def patches(self, env, srcdir):
        return ['cross-config-script.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://downloads.apache.org/apr/apr-util-%s.tar.bz2'
            % self.version(),
            target,
            sha256=(
                '96de1dd6f6a0476d2d2e7964926d8c1ddc3bb0e210e1b1812d3ba5a454a392e2'
            ),
        )

    def configure(self, env, srcdir):
        sysroot = env['PORTS_SYSROOT']
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                '--with-apr=%s/usr/bin/apr-1-config' % sysroot,
                '--with-expat=%s/usr' % sysroot,
                '--with-dbm=sdbm',
                '--includedir=/usr/include/apr-1',
                '--disable-util-dso',
                '--without-apr-iconv',
                '--without-crypto',
                '--without-openssl',
                '--without-nss',
                '--without-commoncrypto',
                '--without-ldap',
                '--without-gdbm',
                '--without-ndbm',
                '--without-berkeley-db',
                '--without-pgsql',
                '--without-mysql',
                '--without-sqlite3',
                '--without-sqlite2',
                '--without-oracle',
                '--without-odbc',
            ),
        )
        self._prepare_libtool(env, srcdir)

    def build(self, env, srcdir):
        steps.make(
            srcdir,
            env,
            inplace=False,
            extra_opts=self._make_options(env, srcdir),
        )

    def deploy(self, env, srcdir, deploydir):
        steps.make(
            srcdir,
            env,
            target='install',
            inplace=False,
            extra_opts=(
                ('DESTDIR=%s' % deploydir),
            ) + self._make_options(env, srcdir),
        )

    @staticmethod
    def _libtool_path(srcdir, env):
        return os.path.join(
            steps.get_builddir(srcdir, env, False), 'pedigree-libtool'
        )

    def _prepare_libtool(self, env, srcdir):
        source_path = os.path.join(
            env['PORTS_SYSROOT'],
            'usr',
            'share',
            'apr-1',
            'build',
            'libtool',
        )
        with open(source_path, encoding='utf-8') as source:
            contents = source.read()
        replacements = (
            (
                'lt_sysroot=\n',
                "lt_sysroot='%s'\n" % env['PORTS_SYSROOT'],
            ),
            ('hardcode_into_libs=yes', 'hardcode_into_libs=no'),
            ('hardcode_libdir_flag_spec="\\$wl-rpath \\$wl\\$libdir"',
             'hardcode_libdir_flag_spec=""'),
            ('hardcode_action=immediate', 'hardcode_action=unsupported'),
        )
        for old, new in replacements:
            if old not in contents:
                raise RuntimeError('APR libtool is missing setting: %s' % old)
            contents = contents.replace(old, new, 1)
        with open(
            self._libtool_path(srcdir, env), 'w', encoding='utf-8'
        ) as destination:
            destination.write(contents)

    def _make_options(self, env, srcdir):
        apr_builddir = os.path.join(
            env['PORTS_SYSROOT'], 'usr', 'share', 'apr-1', 'build'
        )
        return (
            'apr_builddir=%s' % apr_builddir,
            'apr_builders=%s' % apr_builddir,
            'LIBTOOL=/bin/sh %s' % self._libtool_path(srcdir, env),
            'CC=%s' % env['CROSS_CC'],
            'CPP=%s' % env['CROSS_CPP'],
            'CPPFLAGS=%s' % env['CPPFLAGS'],
            'LDFLAGS=%s' % env['LDFLAGS'],
        )

    def postdeploy(self, env, srcdir, deploydir):
        metadata = (
            os.path.join(deploydir, 'usr', 'bin', 'apu-1-config'),
            os.path.join(deploydir, 'usr', 'lib', 'libaprutil-1.la'),
            os.path.join(
                deploydir, 'usr', 'lib', 'pkgconfig', 'apr-util-1.pc'
            ),
        )
        for path in metadata:
            if not os.path.isfile(path):
                continue
            with open(path, encoding='utf-8') as source:
                contents = source.read()
            for build_path in (
                os.path.realpath(steps.get_builddir(srcdir, env, False)),
                os.path.realpath(srcdir),
                steps.get_builddir(srcdir, env, False),
                srcdir,
                env.get('PORTS_SYSROOT', ''),
                env.get('TARGET_SYSROOT', ''),
                env.get('APPS_BASE', ''),
                env.get('CROSS_BASE', ''),
            ):
                if build_path:
                    contents = contents.replace(build_path, '')
            if path.endswith('.la'):
                contents = contents.replace('//usr/', '/usr/')
                contents = contents.replace('-L/', '-L=/')
                contents = contents.replace('-R/', '-R=/')
                contents = re.sub(
                    r"(?<![=A-Za-z0-9_])/(usr|lib)/([^ \t'\"\n]+\.la)",
                    r'=/\1/\2',
                    contents,
                )
            with open(path, 'w', encoding='utf-8') as destination:
                destination.write(contents)

        config_script = os.path.join(
            deploydir, 'usr', 'bin', 'apu-1-config'
        )
        if not os.path.isfile(config_script):
            raise RuntimeError('APR-util did not install apu-1-config')
        expected = {
            '--bindir': ['/usr/bin'],
            '--includedir': [
                os.path.join(deploydir, 'usr', 'include', 'apr-1')
            ],
            '--includes': [
                '-I' + os.path.join(deploydir, 'usr', 'include', 'apr-1'),
                '-I' + os.path.join(deploydir, 'usr', 'include'),
            ],
            '--ldflags': [
                '-L' + os.path.join(deploydir, 'usr', 'lib')
            ],
            '--link-ld': [
                '-L' + os.path.join(deploydir, 'usr', 'lib'),
                '-laprutil-1',
            ],
            '--link-libtool': [
                os.path.join(deploydir, 'usr', 'lib', 'libaprutil-1.la')
            ],
        }
        for option, expected_flags in expected.items():
            actual_flags = subprocess.check_output(
                ['/bin/sh', config_script, option], text=True
            ).split()
            if actual_flags != expected_flags:
                raise RuntimeError(
                    'apu-1-config %s is not cross-sysroot safe: %r'
                    % (option, actual_flags)
                )
