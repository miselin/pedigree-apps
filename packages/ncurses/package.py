
import os

from support import buildsystem
from support import steps


class NcursesPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(NcursesPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'ncurses'

    def version(self):
        return '6.6'

    def patches(self, env, srcdir):
        return ['pedigree-shared.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='355b4cbbed880b0381a04c46617b7656e362585d52e9cf84a67e2009b749ff11')

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            not_paths=('docdir',),
            extra_config=(
                '--with-shared', '--with-normal', '--without-cxx-binding',
                '--without-ada', '--without-tests', '--disable-stripping',
                '--enable-widec', '--with-termlib', '--enable-pc-files',
                '--with-pkg-config-libdir=/usr/lib/pkgconfig',
                '--with-default-terminfo-dir=/usr/share/terminfo',
                '--with-terminfo-dirs=/etc/terminfo:/usr/share/terminfo'))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install', extra_opts=(
            'DESTDIR=%s' % deploydir,))

    def postdeploy(self, env, srcdir, deploydir):
        config = os.path.join(deploydir, 'usr', 'bin', 'ncursesw6-config')
        with open(config, encoding='utf-8') as source:
            contents = source.read()
        library_dir = os.path.join(env['PORTS_SYSROOT'], 'usr', 'lib')
        contents = contents.replace('-L%s' % library_dir, '')
        contents = contents.replace('-Wl,-rpath-link,%s' % library_dir, '')
        with open(config, 'w', encoding='utf-8') as destination:
            destination.write(contents)

        pkgconfig_dir = os.path.join(
            deploydir, 'usr', 'lib', 'pkgconfig')
        for filename in sorted(os.listdir(pkgconfig_dir)):
            if not filename.endswith('.pc'):
                continue
            path = os.path.join(pkgconfig_dir, filename)
            with open(path, encoding='utf-8') as source:
                contents = source.read()
            contents = contents.replace('-L%s' % library_dir, '')
            contents = contents.replace(
                '-Wl,-rpath-link,%s' % library_dir, '')
            with open(path, 'w', encoding='utf-8') as destination:
                destination.write(contents)
