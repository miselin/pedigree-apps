
import os

from support import buildsystem
from support import steps


class PangoPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(PangoPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'pango'

    def version(self):
        return '1.37.2'

    def build_requires(self):
        return ['libtool', 'glib', 'harfbuzz', 'libfreetype', 'cairo']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnome.org/pub/GNOME/sources/%(package)s/1.37/%(package)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(srcdir, env)
        steps.autoreconf(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        # Wipe out the test Makefile (only linker tests).
        # TODO(miselin): fix this rather than rip out the Makefile
        ignore_makefile = '''
ign:
\t@echo '<ignored>'
all: ign
install: ign
clean: ign
'''

        with open(os.path.join(srcdir, 'tests', 'Makefile'), 'w') as f:
            f.write(ignore_makefile)

        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
