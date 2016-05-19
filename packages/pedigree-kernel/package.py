
import os

from support import buildsystem
from support import steps


class Pedigree_kernelPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Pedigree_kernelPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'pedigree-kernel'

    def version(self):
        return '0.1'

    def deploy(self, env, srcdir, deploydir):
        # TODO: this should install a versioned file, maybe?
        os.makedirs(os.path.join(deploydir, 'boot'))
        os.makedirs(os.path.join(deploydir, 'support', 'pedigree'))
        steps.cmd(['cp', '-a',
            os.path.join(env['PEDIGREE_BASE'], 'build', 'kernel', 'kernel'),
            os.path.join(deploydir, 'boot', 'kernel')])
        steps.cmd(['cp', '-a',
            os.path.join(env['PEDIGREE_BASE'], 'build', 'kernel',
                         'kernel.debug'),
            os.path.join(deploydir, 'support', 'pedigree', 'kernel.debug')])
