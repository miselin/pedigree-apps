
import os

from support import buildsystem
from support import steps


class LibtoolPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibtoolPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libtool'

    def version(self):
        return '2.4.2'

    def patches(self, env, srcdir):
        return ['libtool.m4.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=('--enable-shared',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, 'install')

    def links(self, env, deploydir, cross_dir):
        libs = ['libltdl.a', 'libltdl.so', 'libltdl.la']
        headers = ['ltdl.h', 'libltdl']
        steps.symlinks(deploydir, cross_dir, libs=libs, headers=headers)

        # We have to copy the scripts by hand as they need to be modified.
        bins = ['libtoolize', 'libtool']
        target_path = os.path.join(cross_dir, 'bin')

        for bin in bins:
            source_contents = ''
            with open(os.path.join(deploydir, 'applications', bin), 'r') as f:
                source_contents = f.read()

            # Replace absolute paths inside so they work with our cross
            # toolchain properly. The better fix for this is to use a chroot.
            replacements = ['applications', 'libraries', 'include', 'support']
            for replacement in replacements:
                source_contents = source_contents.replace('/%s' % replacement,
                    os.path.join(deploydir, replacement))

            target_file = os.path.join(target_path, bin)
            if os.path.isfile(target_file) or os.path.islink(target_file):
                os.unlink(target_file)

            print 'fixing paths inside %s -> %s' % (bin, target_file)
            with open(target_file, 'w') as f:
                f.write(source_contents)

            # Mark the target executable now that we've copied the contents.
            os.chmod(target_file, 0755)
