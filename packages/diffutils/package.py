
from support import buildsystem
from support import steps


class DiffutilsPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(DiffutilsPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'diffutils'

    def version(self):
        return '3.12'

    def build_requires(self):
        return ['gettext']

    def patches(self, env, srcdir):
        return ['pselect-null.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='7c8b7f9fc8609141fdea9cece85249d308624391ff61dedaf528fcb337727dfd')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--enable-cross-guesses=conservative',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
