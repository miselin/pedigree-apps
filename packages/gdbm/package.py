
from support import buildsystem
from support import steps


class GdbmPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(GdbmPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'gdbm'

    def version(self):
        return '1.26'

    def patches(self, env, srcdir):
        return ['pedigree-timing.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='6a24504a14de4a744103dcb936be976df6fbe88ccff26065e54c1c47946f4a5e')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--enable-shared', '--enable-static', '--without-readline'))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
