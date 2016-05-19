
import os

from support import buildsystem
from support import steps


class Pedigree_basePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Pedigree_basePackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'pedigree-base'

    def version(self):
        return '0.1'

    def deploy(self, env, srcdir, deploydir):
        pedigree = os.path.join(env['PEDIGREE_BASE'], 'images')

        copies = [
            (os.path.join(pedigree, 'base', 'system'), deploydir),
            (os.path.join(pedigree, 'base', 'config'), deploydir),
            (os.path.join(pedigree, 'base', '.bashrc'), deploydir),
            (os.path.join(pedigree, 'base', '.profile'), deploydir),
        ]

        for source, dest in copies:
            steps.cmd(['cp', '-ar', source, dest])
