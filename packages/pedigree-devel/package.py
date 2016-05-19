
import os

from support import buildsystem
from support import steps


class Pedigree_develPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Pedigree_develPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'pedigree-devel'

    def version(self):
        return '0.1'

    def deploy(self, env, srcdir, deploydir):
        # Copy from Pedigree to the deployment directory.
        include_dir = os.path.join(deploydir, 'include')
        libs_dir = os.path.join(deploydir, 'libraries')

        pedigree_image = os.path.join(env['PEDIGREE_BASE'], 'images')
        pedigree_build = os.path.join(env['PEDIGREE_BASE'], 'build')

        gcc_vers = steps.cmd([env['CROSS_CC'], '-dumpversion'], env=env)
        gcc_vers = gcc_vers.strip()

        copies = [
            # Libraries
            (os.path.join(pedigree_build, 'libc.so'), libs_dir),
            (os.path.join(pedigree_build, 'libg.so'), libs_dir),
            (os.path.join(pedigree_build, 'libm.so'), libs_dir),
            (os.path.join(pedigree_build, 'libc.a'), libs_dir),
            (os.path.join(pedigree_build, 'libg.a'), libs_dir),
            (os.path.join(pedigree_build, 'libm.a'), libs_dir),
            (os.path.join(pedigree_build, 'libpedigree.so'), libs_dir),
            (os.path.join(pedigree_build, 'libpedigree.a'), libs_dir),
            (os.path.join(pedigree_build, 'libpedigree-c.so'), libs_dir),
            (os.path.join(pedigree_build, 'libpedigree-c.a'), libs_dir),
            (os.path.join(pedigree_build, 'libSDL.so'), libs_dir),
            (os.path.join(pedigree_build, 'libSDL.a'), libs_dir),
            (os.path.join(pedigree_build, 'libs', 'libui.so'), libs_dir),
            (os.path.join(pedigree_build, 'libs', 'libui.a'), libs_dir),
            # Runtime (not build as part of GCC build)
            (os.path.join(pedigree_build, 'kernel', 'crt0.o'),
                os.path.join(libs_dir, 'gcc', env['CROSS_TARGET'], gcc_vers)),
            (os.path.join(pedigree_build, 'kernel', 'crti.o'),
                os.path.join(libs_dir, 'gcc', env['CROSS_TARGET'], gcc_vers)),
            (os.path.join(pedigree_build, 'kernel', 'crtn.o'),
                os.path.join(libs_dir, 'gcc', env['CROSS_TARGET'], gcc_vers)),
            # Headers
            (os.path.join(env['PEDIGREE_BASE'], 'src', 'subsys', 'posix',
                'include', '.'), include_dir),
            (os.path.join(env['PEDIGREE_BASE'], 'src', 'subsys', 'native',
                'include', '.'), os.path.join(include_dir, 'native')),
        ]

        for source, dest in copies:
            if not os.path.exists(dest):
                os.makedirs(dest)

            flags = ['-a']
            if os.path.isdir(source):
                flags += ['-r']

            steps.cmd(['cp'] + flags + [source, dest])
