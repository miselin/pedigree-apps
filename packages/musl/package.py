import os

from support import buildsystem
from support import steps


SOURCE_VERSION = "1.2.6"
SOURCE_SHA256 = (
    "d585fd3b613c66151fc3249e8ed44f77020cb5e6c1e635a616d3f9f82460512a"
)


class MuslPackage(buildsystem.Package):

    def name(self):
        return "musl"

    def version(self):
        return SOURCE_VERSION

    def patches(self, env, srcdir):
        return [
            "musl-1.2.6-cve-2026-40200-qsort.patch",
            "musl-1.2.6-cve-2026-6042-iconv.patch",
        ]

    def download(self, env, target):
        steps.download(
            "https://www.musl-libc.org/releases/musl-%s.tar.gz"
            % SOURCE_VERSION,
            target,
            sha256=SOURCE_SHA256,
        )

    def configure(self, env, srcdir):
        command_env = env.copy()
        command_env.update(
            {
                "CC": env["CROSS_CC"],
                "AR": env["CROSS_AR"],
                "RANLIB": env["CROSS_RANLIB"],
                "CROSS_COMPILE": env["CROSS_TARGET"] + "-",
                "CFLAGS": "-O2 -g3 -ggdb -fno-omit-frame-pointer -fPIC",
                # The PUP audit requires a SONAME for shared libraries. musl
                # normally omits one because its loader is named explicitly.
                "LDFLAGS": env["LDFLAGS"].split(" -L", 1)[0]
                + " -Wl,-soname,libc.so",
                "CONFIG_SITE": env["TARGET_CONFIG_SITE"],
            }
        )
        steps.cmd(
            [
                os.path.join(srcdir, "configure"),
                "--target=%s" % env["CROSS_TARGET"],
                "--prefix=/usr",
                "--syslibdir=/usr/lib",
                "--enable-shared",
            ],
            cwd=srcdir,
            env=command_env,
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.make(
            srcdir,
            env,
            target="install",
            extra_opts=("DESTDIR=%s" % deploydir,),
        )

    def postdeploy(self, env, srcdir, deploydir):
        loader = os.path.join(
            deploydir, "usr", "lib", "ld-musl-x86_64.so.1"
        )
        libc = os.path.join(deploydir, "usr", "lib", "libc.so")
        if not os.path.isfile(libc):
            raise RuntimeError("musl did not install usr/lib/libc.so")
        if not os.path.islink(loader):
            raise RuntimeError("musl loader is not a symlink")
        os.unlink(loader)
        os.symlink("libc.so", loader)
