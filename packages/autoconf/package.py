
import os
import subprocess

from support import buildsystem
from support import steps


LATEST_AUTOCONF = '2.69'


class AutoconfBasePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(AutoconfBasePackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        if self.version() == LATEST_AUTOCONF:
            return 'autoconf'
        else:
            return 'autoconf%s' % self.version()

    def version(self):
        return LATEST_AUTOCONF

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/pub/gnu/%(urlpackage)s/%(urlpackage)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
            'urlpackage': 'autoconf',
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.autoreconf(srcdir, env)

    def configure(self, env, srcdir):
        if self.version() != LATEST_AUTOCONF:
            extra_config = ('--program-suffix=-%s' % self.version(),)
        else:
            extra_config = ()

        steps.run_configure(self, srcdir, env, inplace=False,
                            extra_config=extra_config)

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)


extra_types = {}


for vers in ('2.64', '2.63'):
    name = 'Autoconf%sPackage' % vers.replace('.', '_')
    cls_type = type(name, (AutoconfBasePackage,),
                    {'version': lambda self, v=vers: v})
    extra_types[name] = cls_type
