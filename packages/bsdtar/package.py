
from support import buildsystem
from support import steps


class BsdtarPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(BsdtarPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'bsdtar'

    def version(self):
        return '3.8.9'

    def build_requires(self):
        return ['zlib', 'openssl', 'expat']

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://www.libarchive.org/downloads/libarchive-%s.tar.xz'
            % self.version(),
            target,
            sha256='888c934f9d95648ecb9163dc8e23ab80a476ecb81a8f1154704a227b5b676dde',
        )

    def configure(self, env, srcdir):
        env['lt_cv_sys_lib_dlsearch_path_spec'] = ' '.join((
            '%s/usr/lib' % env['PORTS_SYSROOT'],
            '/lib',
            '/usr/lib',
        ))
        env['lt_cv_sys_lib_search_path_spec'] = ' '.join((
            '%s/usr/lib' % env['PORTS_SYSROOT'],
            '%s/lib' % env['TARGET_SYSROOT'],
            '%s/usr/lib' % env['TARGET_SYSROOT'],
        ))
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                '--enable-shared',
                '--enable-static',
                '--enable-bsdtar=shared',
                '--disable-bsdcat',
                '--disable-bsdcpio',
                '--disable-bsdunzip',
                '--disable-rpath',
                '--disable-xattr',
                '--disable-acl',
                '--without-bz2lib',
                '--without-libb2',
                '--without-iconv',
                '--without-lz4',
                '--without-zstd',
                '--without-lzma',
                '--without-cng',
                '--without-mbedtls',
                '--without-nettle',
                '--with-openssl',
                '--without-xml2',
                '--with-expat',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
