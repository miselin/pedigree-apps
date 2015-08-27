
import os

from support import buildsystem
from support import steps


class PrboomPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(PrboomPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'prboom'

    def version(self):
        return '2.5.0'

    def build_requires(self):
        return ['libiconv', 'libpng', 'cairo', 'pixman', 'fontconfig',
                'expat', 'libfreetype']

    def patches(self, env, srcdir):
        # libpng diff from https://github.com/archhurd/packages/blob/master/extra/prboom/libpng-1.4.patch
        # This fixes up references to things that don't exist.
        return ['fix_sdl_configure.diff', 'libpng.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://downloads.sourceforge.net/project/%(package)s/%(package)s%%20stable/%(version)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            'ac_cv_path_SDL_CONFIG=/applications/sdl-config', '--disable-gl',
            '--with-waddir=/support/prboom/wads', '--disable-i386-asm',
            '--without-libpng'))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
