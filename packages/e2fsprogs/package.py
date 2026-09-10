
from support import buildsystem
from support import steps


class e2fsprogsPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(e2fsprogsPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'e2fsprogs'

    def version(self):
        return '1.47.4'

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
            'https://www.kernel.org/pub/linux/kernel/people/tytso/e2fsprogs/'
            'v%s/e2fsprogs-%s.tar.xz' % (self.version(), self.version()),
            target,
            sha256='fd5bf388cbdbe006a3d3b318d983b2948382440acc85a87f1e7d108653e8db0b',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                '--enable-elf-shlibs',
                '--disable-nls',
                '--disable-uuidd',
                '--disable-fuse2fs',
                '--disable-tls',
                '--without-pthread',
                '--without-libarchive',
                '--with-root-prefix=/usr',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
