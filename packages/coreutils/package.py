
from support import buildsystem
from support import steps


class CoreutilsPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(CoreutilsPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'coreutils'

    def version(self):
        return '9.11'

    def build_requires(self):
        return ['gettext', 'libgmp']

    def patches(self, env, srcdir):
        return [
            'pselect-null.diff',
            'sync-unsupported.diff',
            'pedigree-musl-locale.diff',
            'lchown-availability.diff',
        ]

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='394024eda0a5955217ceda9cd1201e65dc8fa3aa29c2951135a49521d57c3cc3')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--disable-acl', '--disable-xattr', '--disable-libcap',
            '--disable-libsmack', '--disable-rpath',
            '--without-selinux', '--enable-cross-guesses=conservative'))

    def install_deps(self):
        return ['libgmp']

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
