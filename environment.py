#!/usr/bin/env python3

import functools
import os

from support.util import expand


class OverridableDict(dict):
    def __init__(self, *args, **kwargs):
        self._overrides = set()
        self._tracking = False
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if self._tracking:
            self._overrides.add(key)
            super().__setitem__(key, value)
        elif key not in self._overrides:
            super().__setitem__(key, value)

    def track(self, tracking=True):
        self._tracking = tracking

    def has_overrides(self):
        return bool(self._overrides)


def generate_environment(target_arch, env=None, recurse=True):
    if target_arch != "amd64":
        raise ValueError("only the maintained amd64 target is supported")

    if env is None:
        env = OverridableDict()

    _expand = functools.partial(expand, env)
    apps_base = os.environ.get("PEDIGREE_APPS_ROOT", "/workspace")
    pedigree_base = os.environ.get("PEDIGREE_SOURCE_ROOT", "/pedigree")
    toolchain_root = os.environ.get("PEDIGREE_TOOLCHAIN_ROOT", "/opt/pedigree")
    jobs = os.environ.get("PEDIGREE_APPS_JOBS", str(os.cpu_count() or 1))

    env["ARCH_TARGET"] = "x86_64"
    env["ARCH_BITS"] = "64"
    env["CROSS_TARGET"] = "x86_64-pedigree"

    env["PEDIGREE_BASE"] = pedigree_base
    env["APPS_BASE"] = apps_base
    env["CROSS_BASE"] = toolchain_root
    env["TARGET_SYSROOT"] = _expand("$CROSS_BASE/$CROSS_TARGET")
    env["OUTPUT_BASE"] = _expand("$APPS_BASE/newpacks/$ARCH_TARGET")
    env["SOURCE_BASE"] = _expand("$APPS_BASE/packages")
    env["DOWNLOAD_TEMP"] = _expand("$APPS_BASE/downloads")
    env["BUILD_BASE"] = _expand("$APPS_BASE/.build/$ARCH_TARGET")
    env["TARGET_CONFIG_SITE"] = _expand("$APPS_BASE/config.site")
    env["HOME"] = os.environ.get("HOME", "/tmp")
    env["CCACHE_DIR"] = os.environ.get(
        "CCACHE_DIR", _expand("$BUILD_BASE/ccache")
    )
    env["CCACHE_BASEDIR"] = apps_base
    env["CCACHE_COMPILERCHECK"] = "content"
    env["PACKMAN_TARGET_ARCH"] = target_arch
    env["PACKMAN_PATH"] = _expand("$APPS_BASE/pup")
    env["PACKMAN_SCRIPT"] = "/opt/pedigree-apps/bin/pup"
    env["PACKMAN_REPO"] = _expand("$APPS_BASE/pup/package_repo")
    env["PACKMAN_CONFIG"] = _expand("$BUILD_BASE/pup.conf")

    env["CROSS_CC"] = _expand("$CROSS_BASE/bin/$CROSS_TARGET-gcc")
    env["CROSS_CXX"] = _expand("$CROSS_BASE/bin/$CROSS_TARGET-g++")
    env["CROSS_CPP"] = _expand("$CROSS_BASE/bin/$CROSS_TARGET-cpp")
    env["CROSS_AS"] = _expand("$CROSS_BASE/bin/$CROSS_TARGET-as")
    env["CROSS_LD"] = _expand("$CROSS_BASE/bin/$CROSS_TARGET-ld")
    env["CROSS_AR"] = _expand("$CROSS_BASE/bin/$CROSS_TARGET-ar")
    env["CROSS_RANLIB"] = _expand("$CROSS_BASE/bin/$CROSS_TARGET-ranlib")
    env["CROSS_STRIP"] = _expand("$CROSS_BASE/bin/$CROSS_TARGET-strip")

    env["CC"] = env["CROSS_CC"]
    env["CXX"] = env["CROSS_CXX"]
    env["CPP"] = env["CROSS_CPP"]
    env["AS"] = env["CROSS_AS"]
    env["LD"] = env["CROSS_LD"]
    env["AR"] = env["CROSS_AR"]
    env["RANLIB"] = env["CROSS_RANLIB"]
    env["STRIP"] = env["CROSS_STRIP"]

    common_flags = "-O2 -pipe -m64 -march=x86-64 -D__PEDIGREE__"
    c_flags = common_flags + " -std=gnu17"
    page_flags = "-Wl,-z,max-page-size=4096 -Wl,-z,common-page-size=4096"
    # GCC 15 defaults to C23, but several current GNU releases still use
    # pre-C23 empty-parameter declarations in their portability sources.
    env["CROSS_CFLAGS"] = c_flags
    env["CROSS_CXXFLAGS"] = common_flags
    env["CFLAGS"] = c_flags
    env["CXXFLAGS"] = common_flags
    env["CPPFLAGS"] = ""
    env["LDFLAGS"] = page_flags
    env["LIBS"] = ""
    env["MAKEFLAGS"] = "-j%s" % jobs
    env["LD_LIBRARY_PATH"] = ""

    env["PATH"] = _expand(
        "/opt/pedigree-apps/bin:$CROSS_BASE/bin:"
        "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    )
    env["MAKE"] = "/usr/bin/make"
    env["PATCH"] = "/usr/bin/patch"
    env["AUTOCONF"] = "/usr/bin/autoconf"
    env["AUTORECONF"] = "/usr/bin/autoreconf"
    env["ACLOCAL"] = "/usr/bin/aclocal"
    env["LIBTOOLIZE"] = "/usr/bin/libtoolize"
    env["TAR"] = "/usr/bin/tar"
    env["CCACHE"] = "/usr/bin/ccache"
    env["CMAKE"] = "/usr/bin/cmake"
    env["MESON"] = "/opt/pedigree-apps/bin/meson"
    env["NINJA"] = "/usr/bin/ninja"
    env["PKG_CONFIG"] = "/usr/bin/pkg-config"

    if recurse:
        try:
            from local_environment import modify_environment

            env.track()
            modify_environment(env)
            env.track(tracking=False)
            if env.has_overrides():
                generate_environment(target_arch, env=env, recurse=False)
        except ImportError:
            pass

    return env
