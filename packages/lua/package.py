from support import buildsystem
from support import steps


class LuaPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return "lua"

    def version(self):
        return "5.5.1"

    def patches(self, env, srcdir):
        return ["luaconf.h.diff"]

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://www.lua.org/ftp/lua-%s.tar.gz" % self.version(),
            target,
            sha256=(
                "1c4b4068d67061f2a2231ad2b5422e77"
                "acea1487ea9890f6320af614f4373dce"
            ),
        )

    def _build_options(self, env):
        return (
            "CC=%s" % env["CROSS_CC"],
            "AR=%s rcu" % env["CROSS_AR"],
            "RANLIB=%s" % env["CROSS_RANLIB"],
            "MYCFLAGS=%s" % env["CFLAGS"],
            "MYLDFLAGS=%s" % env["LDFLAGS"],
            "SYSCFLAGS=-DLUA_USE_POSIX -DLUA_USE_DLOPEN",
            "SYSLIBS=-Wl,-E -ldl",
        )

    def build(self, env, srcdir):
        steps.make(
            srcdir,
            env,
            target="generic",
            extra_opts=self._build_options(env),
        )

    def deploy(self, env, srcdir, deploydir):
        steps.make(
            srcdir,
            env,
            target="install",
            extra_opts=(
                "INSTALL_TOP=%s/usr" % deploydir,
                "INSTALL_MAN=%s/usr/share/man/man1" % deploydir,
            ),
        )
