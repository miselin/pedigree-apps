
from support import buildsystem
from support import steps


class GzipPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(GzipPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'gzip'

    def version(self):
        return '1.14'

    def build_requires(self):
        return []

    def install_deps(self):
        return []

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = ('https://ftp.gnu.org/gnu/%(package)s/'
               '%(package)s-%(version)s.tar.xz' % {
                   'package': self.name(),
                   'version': self.version()})
        steps.download(
            url, target,
            sha256='01a7b881bd220bfdf615f97b8718f80bdfd3f6add385b993dcf6efd14e8c0ac6')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--enable-cross-guesses=conservative',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
