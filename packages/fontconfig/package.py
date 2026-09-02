
from support import buildsystem
from support import steps


class FontconfigPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(FontconfigPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'fontconfig'

    def version(self):
        return '2.18.3'

    def build_requires(self):
        return ['expat', 'libfreetype']

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return ['0001-Fixes-for-Pedigree-with-musl-for-libc.patch']

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://gitlab.freedesktop.org/api/v4/projects/890/packages/'
            'generic/fontconfig/%s/fontconfig-%s.tar.xz'
            % (self.version(), self.version()),
            target,
            sha256='4f7b554a38cdf78c033f666c8871f3749e14a094f65a07f630c91ed0b43d35e3',
        )

    def configure(self, env, srcdir):
        steps.meson_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-Ddefault_library=both',
                '-Ddoc=disabled',
                '-Ddoc-txt=disabled',
                '-Ddoc-man=disabled',
                '-Ddoc-pdf=disabled',
                '-Ddoc-html=disabled',
                '-Dnls=disabled',
                '-Dtests=disabled',
                '-Dtools=enabled',
                '-Dcache-build=disabled',
                '-Diconv=disabled',
                '-Dxml-backend=expat',
                '-Dfontations=disabled',
                '-Dcache-dir=/var/cache/fontconfig',
                '-Dtemplate-dir=/usr/share/fontconfig/conf.avail',
                '-Dbaseconfig-dir=/etc/fonts',
                '-Dconfig-dir=/etc/fonts/conf.d',
                '-Dxml-dir=/usr/share/xml/fontconfig',
            ),
        )

    def build(self, env, srcdir):
        steps.meson_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.meson_install(srcdir, env, deploydir)
