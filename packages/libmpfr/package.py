
from support import buildsystem
from support import steps


class LibmpfrPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibmpfrPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'libmpfr'

    def version(self):
        return '4.2.2'

    def build_requires(self):
        return ['libgmp']

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://ftp.gnu.org/gnu/mpfr/mpfr-%s.tar.xz'
            % self.version(),
            target,
            sha256='b67ba0383ef7e8a8563734e2e889ef5ec3c3b898a01d00fa0a6869ad81c6ce01',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                '--enable-shared',
                '--enable-static',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
