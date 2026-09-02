import os
import shutil

from support import buildsystem
from support import steps


SOURCE_VERSION = "2.46.1"
TOOLCHAIN_RECIPE = 2
MAINLINE_PATCH_SHA256 = (
    "3b50acd10cfeaa14d89acfb6889db6b90"
    "e41db5db19c7cc4e879e4ee37cc1681"
)


class BinutilsPackage(buildsystem.Package):

    BUILD_TARGETS = ("all-binutils", "all-gas", "all-ld")
    INSTALL_TARGETS = (
        "install-binutils",
        "install-gas",
        "install-ld",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = "xz"

    def name(self):
        return "binutils"

    def version(self):
        return SOURCE_VERSION

    def build_requires(self):
        return ["zlib"]

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return ["pedigree-binutils.diff"]

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://sourceware.org/pub/binutils/releases/"
            "binutils-%s.tar.xz" % SOURCE_VERSION,
            target,
            sha256=(
                "e127a709cba24c76de8936cb7083dd76"
                "8f28cd37eb010492e2f19b71eb1294e4"
            ),
        )

    def _native_tool(self, name):
        path = shutil.which(name)
        if not path:
            raise RuntimeError(
                "target-native binutils build requires host %s" % name
            )
        return path

    def _canadian_environment(self, env):
        # CC builds Pedigree executables, while *_FOR_BUILD must remain Linux
        # tools that can run inside the builder during this Canadian cross.
        command_env = env.copy()
        command_env.update(
            {
                "AR_FOR_BUILD": self._native_tool("ar"),
                "CC_FOR_BUILD": self._native_tool("cc"),
                "CXX_FOR_BUILD": self._native_tool("c++"),
                "RANLIB_FOR_BUILD": self._native_tool("ranlib"),
                "AR_FOR_TARGET": env["CROSS_AR"],
                "AS_FOR_TARGET": env["CROSS_AS"],
                "CC_FOR_TARGET": env["CROSS_CC"],
                "CXX_FOR_TARGET": env["CROSS_CXX"],
                "LD_FOR_TARGET": env["CROSS_LD"],
                "NM_FOR_TARGET": os.path.join(
                    env["CROSS_BASE"],
                    "bin",
                    env["CROSS_TARGET"] + "-nm",
                ),
                "RANLIB_FOR_TARGET": env["CROSS_RANLIB"],
                "CONFIG_SITE": env["TARGET_CONFIG_SITE"],
            }
        )
        return command_env

    def configure(self, env, srcdir):
        command_env = self._canadian_environment(env)
        build_triplet = steps.cmd_output(
            [os.path.join(srcdir, "config.guess")],
            cwd=srcdir,
            env=command_env,
            text=True,
        ).strip()
        builddir = steps.get_builddir(srcdir, env, False)
        steps.cmd(
            [
                os.path.join(srcdir, "configure"),
                "--build=%s" % build_triplet,
                "--host=%s" % env["CROSS_TARGET"],
                "--target=%s" % env["CROSS_TARGET"],
                "--prefix=/usr",
                "--exec-prefix=/usr",
                "--bindir=/usr/bin",
                "--libdir=/usr/lib",
                "--libexecdir=/usr/lib/binutils",
                "--datarootdir=/usr/share",
                "--mandir=/usr/share/man",
                "--infodir=/usr/share/info",
                "--docdir=/usr/share/doc/binutils",
                # The installed native linker searches the running system,
                # never the transient dependency staging root.
                "--with-sysroot=/",
                "--with-system-zlib",
                "--disable-nls",
                "--disable-gold",
                "--disable-gprofng",
                "--disable-multilib",
                "--disable-werror",
                "--disable-shared",
                "--enable-static",
                "--enable-ld=default",
                "--enable-lto",
                "--without-debuginfod",
                "--without-zstd",
            ],
            cwd=builddir,
            env=command_env,
        )

    def build(self, env, srcdir):
        command_env = self._canadian_environment(env)
        for target in self.BUILD_TARGETS:
            steps.make(
                srcdir,
                command_env,
                target=target,
                inplace=False,
            )

    def deploy(self, env, srcdir, deploydir):
        command_env = self._canadian_environment(env)
        command_env["DESTDIR"] = deploydir
        for target in self.INSTALL_TARGETS:
            steps.make(
                srcdir,
                command_env,
                target=target,
                inplace=False,
            )

    def postdeploy(self, env, srcdir, deploydir):
        for root, _, filenames in os.walk(deploydir):
            for filename in filenames:
                if filename.endswith(".la"):
                    os.unlink(os.path.join(root, filename))

        missing = [
            name
            for name in ("as", "ld", "objdump", "readelf")
            if not os.path.isfile(
                os.path.join(deploydir, "usr", "bin", name)
            )
        ]
        if missing:
            raise RuntimeError(
                "target-native binutils tools were not installed: %s"
                % ", ".join(missing)
            )
