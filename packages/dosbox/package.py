
import os

from support import buildsystem
from support import steps


class DosboxPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(DosboxPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'dosbox'

    def version(self):
        return '0.74'

    def build_requires(self):
        return ['libiconv', 'libpng', 'cairo', 'pixman', 'fontconfig',
                'expat', 'libfreetype']

    def patches(self, env, srcdir):
        return ['status.h.diff', '0001-Ensure-offsetof-is-present.patch']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://sourceforge.net/projects/%(package)s/files/%(package)s/%(version)s/%(package)s-%(version)s.tar.gz/download' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            'ac_cv_path_SDL_CONFIG=/applications/sdl-config',
            '--disable-alsatest', '--disable-opengl', '--enable-core-inline',
            '--enable-dynamic-core', '--enable-dynrec', '--enable-fpu',
            '--enable-fpu-x86', '--disable-unaligned-memory'))

    def build(self, env, srcdir):
        steps.make(srcdir, env, parallel=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
