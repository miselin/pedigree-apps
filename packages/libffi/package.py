
from support import buildsystem
from support import steps


class LibffiPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibffiPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'gz'

    def name(self):
        return 'libffi'

    def version(self):
        return '3.8.0'

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
            'https://github.com/libffi/libffi/releases/download/v%s/'
            'libffi-%s.tar.gz' % (self.version(), self.version()),
            target,
            sha256='7da3e2d9a171eb0a038f592ecad3ff2bb2550f3496d87b3b29ad0cf4430c0db4',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self, srcdir, env, inplace=False,
            extra_config=(
                '--disable-docs',
                '--enable-shared',
                '--enable-static',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
