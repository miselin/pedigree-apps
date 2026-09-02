
import os

from support import buildsystem
from support import steps


class GettextPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(GettextPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'gettext'

    def version(self):
        return '1.0'

    def options(self):
        return self._options

    def patches(self, env, srcdir):
        return ['pedigree-musl.diff', 'pselect-null.diff']

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='71132a3fb71e68245b8f2ac4e9e97137d3e5c02f415636eb508ae607bc01add7')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--disable-threads', '--disable-shared', '--enable-static',
            '--disable-java', '--disable-csharp', '--disable-openmp',
            '--disable-acl', '--disable-xattr', '--without-selinux',
            '--without-emacs', '--without-git', '--disable-libasprintf',
            '--enable-cross-guesses=conservative'))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, 'install')

    def postdeploy(self, env, srcdir, deploydir):
        # `spit` is an optional Ollama helper whose Python requests dependency
        # is outside this catalog; do not install a known-unusable command.
        spit = os.path.join(deploydir, 'usr', 'bin', 'spit')
        if os.path.exists(spit):
            os.unlink(spit)

        # Upstream ships this prebuilt Windows/.NET fixture in its examples.
        # It is not usable on Pedigree and should not enter a target package.
        fixture = os.path.join(
            deploydir,
            'usr', 'share', 'doc', 'gettext', 'examples', 'build-aux',
            'csharpexec-test.exe',
        )
        if os.path.exists(fixture):
            os.unlink(fixture)

    def links(self, env, deploydir, cross_dir):
        libs = ['libgettextpo.a', 'libintl.a']
        headers = ['gettext-po.h', 'libintl.h']
        steps.symlinks(deploydir, cross_dir, libs=libs, headers=headers)
