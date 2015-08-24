
import os

from support import buildsystem
from support import steps


class CairoPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(CairoPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'cairo'

    def version(self):
        return '1.12.10'

    def build_requires(self):
        return ['libtool', 'libpng', 'zlib', 'libfreetype', 'fontconfig',
                'pixman', 'glib']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://cairographics.org/releases/%(package)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(srcdir, env)
        env['NOCONFIGURE'] = 'yes'
        steps.cmd([os.path.join(srcdir, 'autogen.sh')], cwd=srcdir, env=env)

    def configure(self, env, srcdir):
        # similar to pixman, without this the build goes crazy
        env['CPPFLAGS'] = '-DCAIRO_NO_MUTEX=1'
        steps.run_configure(self, srcdir, env, extra_config=(
            '--disable-xcd', '--disable-xlib', '--without-x', '--disable-ps',
            '--disable-pdf', '--enable-shared', '--disable-full-testing'))

    def build(self, env, srcdir):
        # Fudge the test makefiles because Cairo's test assume all features
        # are actually enabled.
        ignore_makefile = '''
ign:
\t@echo '<ignored>'

all: ign

install: ign

clean: ign
'''

        with open(os.path.join(srcdir, 'test', 'Makefile'), 'w') as f:
            f.write(ignore_makefile)
        with open(os.path.join(srcdir, 'perf', 'Makefile'), 'w') as f:
            f.write(ignore_makefile)

        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
