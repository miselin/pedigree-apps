
import os

from support import buildsystem
from support import steps


class Pedigree_modulesPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Pedigree_modulesPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'pedigree-modules'

    def version(self):
        return '0.1'

    def deploy(self, env, srcdir, deploydir):
        os.makedirs(os.path.join(deploydir, 'support', 'pedigree'))
        os.makedirs(os.path.join(deploydir, 'system', 'modules'))

        # Pre-built initrd with all modules.
        steps.cmd(['cp', '-a',
            os.path.join(env['PEDIGREE_BASE'], 'build', 'initrd.tar'),
            os.path.join(deploydir, 'support', 'pedigree', 'initrd.tar')])

        # Raw module files (for building a custom initrd).
        steps.cmd(['cp', '-ar',
            os.path.join(env['PEDIGREE_BASE'], 'build', 'modules', '.'),
            os.path.join(deploydir, 'system', 'modules')])
        steps.cmd(['cp', '-ar',
            os.path.join(env['PEDIGREE_BASE'], 'build', 'subsystems', '.'),
            os.path.join(deploydir, 'system', 'modules')])
        steps.cmd(['cp', '-ar',
            os.path.join(env['PEDIGREE_BASE'], 'build', 'drivers', '.'),
            os.path.join(deploydir, 'system', 'modules')])
