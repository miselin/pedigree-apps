import os
import shutil

from support import buildsystem
from support import steps


SOURCE_VERSION = "15.3.0"
TOOLCHAIN_RECIPE = 2
MAINLINE_PATCH_SHA256 = (
    "c4e4af9f48b9c2e63a443fd793294890"
    "428de1acfe476735f77037308fbd8d2b"
)


class GccPackage(buildsystem.Package):

    BUILD_TARGETS = (
        "all-gcc",
        "all-target-libgcc",
        "all-target-libstdc++-v3",
    )
    INSTALL_TARGETS = (
        "install-gcc",
        "install-target-libgcc",
        "install-target-libstdc++-v3",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = "xz"

    def name(self):
        return "gcc"

    def version(self):
        return SOURCE_VERSION

    def release_version(self):
        # Preserve the immutable release containing the relative header paths.
        return self.version() + ".1"

    def build_requires(self):
        return ["binutils", "libgmp", "libmpfr", "libmpc", "zlib"]

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return [
            "pedigree-gcc.diff",
            "canadian-build-flags.diff",
            "modules-madvise.diff",
        ]

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://ftp.gnu.org/gnu/gcc/gcc-%s/gcc-%s.tar.xz"
            % (SOURCE_VERSION, SOURCE_VERSION),
            target,
            sha256=(
                "fa59c1beef8995f27c4d71c1df227587"
                "189315d3e6faff1bb4306e61b0c530eb"
            ),
        )

    def prebuild(self, env, srcdir):
        # GCC's LTO plugin is a host shared object even when target libgcc and
        # libstdc++ remain static. Generated Libtool fragments otherwise treat
        # Pedigree as a platform without shared-library support and silently
        # omit liblto_plugin.so.
        steps.patch_libtool_configure(srcdir)

    def _native_tool(self, name):
        path = shutil.which(name)
        if not path:
            raise RuntimeError(
                "target-native GCC build requires host %s" % name
            )
        return path

    def _canadian_environment(self, env):
        # The existing cross compiler builds the Pedigree-hosted compiler and
        # its target libraries. Build generators must stay Linux-native.
        command_env = env.copy()
        command_env.update(
            {
                "AR_FOR_BUILD": self._native_tool("ar"),
                "CC_FOR_BUILD": self._native_tool("cc"),
                "CXX_FOR_BUILD": self._native_tool("c++"),
                "RANLIB_FOR_BUILD": self._native_tool("ranlib"),
                "CFLAGS_FOR_BUILD": "-O2",
                "CXXFLAGS_FOR_BUILD": "-O2",
                "CPPFLAGS_FOR_BUILD": "",
                "LDFLAGS_FOR_BUILD": "",
                "AR_FOR_TARGET": env["CROSS_AR"],
                "AS_FOR_TARGET": env["CROSS_AS"],
                "CC_FOR_TARGET": env["CROSS_CC"],
                "CXX_FOR_TARGET": env["CROSS_CXX"],
                "GCC_FOR_TARGET": env["CROSS_CC"],
                "LD_FOR_TARGET": env["CROSS_LD"],
                "NM_FOR_TARGET": os.path.join(
                    env["CROSS_BASE"],
                    "bin",
                    env["CROSS_TARGET"] + "-nm",
                ),
                "RANLIB_FOR_TARGET": env["CROSS_RANLIB"],
                # libgcc and libstdc++ are intentionally static, but Pedigree
                # DSOs consume them, so retain the r2 bootstrap's PIC contract.
                "CFLAGS_FOR_TARGET": env["CROSS_CFLAGS"] + " -fPIC",
                "CXXFLAGS_FOR_TARGET": env["CROSS_CXXFLAGS"] + " -fPIC",
                "LDFLAGS_FOR_TARGET": env["LDFLAGS"],
                "CONFIG_SITE": env["TARGET_CONFIG_SITE"],
            }
        )
        return command_env

    def _make_options(self, env):
        # GCC exports this value to its sub-configures and compiles it into
        # both the driver and plugin compatibility header. Keep the target
        # configuration useful without publishing transient build roots.
        target_configuration = " ".join(
            (
                "--host=%s" % env["CROSS_TARGET"],
                "--target=%s" % env["CROSS_TARGET"],
                "--prefix=/usr",
                "--with-sysroot=/",
                "--with-native-system-header-dir=/usr/include",
                "--with-as=/usr/bin/as",
                "--with-ld=/usr/bin/ld",
                "--enable-languages=c,c++",
                "--enable-threads=posix",
                "--enable-version-specific-runtime-libs",
                "--enable-lto",
                "--disable-multilib",
                "--disable-nls",
            )
        )
        return ("TOPLEVEL_CONFIGURE_ARGUMENTS=" + target_configuration,)

    def configure(self, env, srcdir):
        command_env = self._canadian_environment(env)
        build_triplet = steps.cmd_output(
            [os.path.join(srcdir, "config.guess")],
            cwd=srcdir,
            env=command_env,
            text=True,
        ).strip()
        builddir = steps.get_builddir(srcdir, env, False)
        dependency_prefix = os.path.join(env["PORTS_SYSROOT"], "usr")
        # GCC's native default keeps the versioned headers and runtime together.
        # An explicit C++ include path becomes relative with the '/' sysroot.
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
                "--libexecdir=/usr/lib",
                "--datarootdir=/usr/share",
                "--mandir=/usr/share/man",
                "--infodir=/usr/share/info",
                "--docdir=/usr/share/doc/gcc",
                # These are target paths embedded in the installed compiler.
                # Build-only dependencies still come from PORTS_SYSROOT.
                "--with-sysroot=/",
                "--with-native-system-header-dir=/usr/include",
                "--with-as=/usr/bin/as",
                "--with-ld=/usr/bin/ld",
                "--with-gmp=%s" % dependency_prefix,
                "--with-mpfr=%s" % dependency_prefix,
                "--with-mpc=%s" % dependency_prefix,
                "--with-system-zlib",
                "--enable-languages=c,c++",
                "--enable-threads=posix",
                "--enable-version-specific-runtime-libs",
                "--enable-lto",
                "--disable-bootstrap",
                "--disable-libstdcxx-pch",
                "--disable-multilib",
                "--disable-nls",
                "--disable-shared",
                "--enable-static",
                "--disable-werror",
                "--without-newlib",
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
                extra_opts=self._make_options(env),
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
                extra_opts=self._make_options(env),
            )

    def postdeploy(self, env, srcdir, deploydir):
        for root, _, filenames in os.walk(deploydir):
            for filename in filenames:
                if filename.endswith(".la"):
                    os.unlink(os.path.join(root, filename))

        runtime = os.path.join(
            "usr", "lib", "gcc", env["CROSS_TARGET"], SOURCE_VERSION
        )
        include = os.path.join(runtime, "include", "c++")
        required = (
            os.path.join("usr", "bin", "gcc"),
            os.path.join("usr", "bin", "g++"),
            os.path.join(include, "algorithm"),
            os.path.join(include, "cstdlib"),
            os.path.join(include, env["CROSS_TARGET"], "bits", "c++config.h"),
            os.path.join(runtime, "cc1"),
            os.path.join(runtime, "cc1plus"),
            os.path.join(runtime, "liblto_plugin.so"),
            os.path.join(runtime, "libstdc++.a"),
            os.path.join(runtime, "libstdc++exp.a"),
            os.path.join(runtime, "libsupc++.a"),
            os.path.join(runtime, "libstdc++.a-gdb.py"),
            os.path.join(runtime, "libstdc++.modules.json"),
            os.path.join(runtime, "plugin", "include", "configargs.h"),
        )
        missing = [
            relative
            for relative in required
            if not os.path.isfile(os.path.join(deploydir, relative))
        ]
        if missing:
            raise RuntimeError(
                "target-native GCC components were not installed: %s"
                % ", ".join(missing)
            )

        configargs = os.path.join(deploydir, required[-1])
        with open(configargs, "rb") as config_file:
            content = config_file.read()
        leaked = [
            value
            for value in (
                env.get("APPS_BASE"),
                env.get("CROSS_BASE"),
                env.get("PORTS_SYSROOT"),
            )
            if value and value.encode() in content
        ]
        if leaked:
            raise RuntimeError(
                "installed GCC configuration contains build paths: %s"
                % ", ".join(leaked)
            )
