
from support import buildsystem
from support import steps


class LibPipelinePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibPipelinePackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'gz'

    def name(self):
        return 'libpipeline'

    def version(self):
        return '1.5.8'

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
            'https://download-mirror.savannah.gnu.org/releases/libpipeline/'
            'libpipeline-%s.tar.gz' % self.version(),
            target,
            sha256='1b1203ca152ccd63983c3f2112f7fe6fa5afd453218ede5153d1b31e11bb8405',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                '--enable-threads=posix',
                '--enable-shared',
                '--enable-static',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
