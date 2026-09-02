
from support import buildsystem
from support import steps


class Libpcre2Package(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Libpcre2Package, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'bz2'

    def name(self):
        return 'libpcre2'

    def version(self):
        return '10.48'

    def build_requires(self):
        return []

    def install_deps(self):
        return []

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://github.com/PCRE2Project/pcre2/releases/download/'
            'pcre2-%s/pcre2-%s.tar.bz2' % (self.version(), self.version()),
            target,
            sha256='b6c68fdf6f3ac31388b50aa89ff0fc49c00c987c16e7b5146491d12003f2c8ed',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self, srcdir, env, inplace=False,
            extra_config=(
                '--disable-jit',
                '--enable-unicode',
                '--enable-shared',
                '--enable-static',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)


class LibpcrePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibpcrePackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'gz'

    def name(self):
        return 'libpcre'

    def version(self):
        # 8.45 is the final legacy PCRE1 release. New code should use libpcre2.
        return '8.45'

    def build_requires(self):
        return []

    def install_deps(self):
        return []

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://downloads.sourceforge.net/project/pcre/pcre/%s/'
            'pcre-%s.tar.gz' % (self.version(), self.version()),
            target,
            sha256='4e6ce03e0336e8b4a3d6c2b70b1c5e18590a5673a98186da90d4f33c23defc09',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self, srcdir, env, inplace=False,
            extra_config=(
                '--disable-cpp',
                '--disable-jit',
                '--enable-utf',
                '--enable-unicode-properties',
                '--enable-shared',
                '--enable-static',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
