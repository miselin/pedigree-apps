import os
import re

from support import buildsystem
from support import steps


class Python3Package(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = "xz"

    def name(self):
        return "python3"

    def version(self):
        return "3.14.7"

    def build_requires(self):
        return [
            "ca-certificates",
            "gdbm",
            "libffi",
            "ncurses",
            "openssl",
            "readline",
            "sqlite",
            "zlib",
        ]

    def install_deps(self):
        # CPython extension modules retain dynamic links to these libraries.
        return self.build_requires()

    def patches(self, env, srcdir):
        return ["pedigree-cross.diff"]

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://www.python.org/ftp/python/%s/Python-%s.tar.xz"
            % (self.version(), self.version()),
            target,
            sha256=(
                "3b48dac8fb59f62eaa67ac83c1eb12bd"
                "a1b7a08406dd286e252c11a66be27f81"
            ),
        )

    def _host_builddir(self, srcdir):
        return os.path.join(srcdir, "pedigree-host-build")

    def _host_python(self, srcdir):
        return os.path.join(self._host_builddir(srcdir), "python-host")

    def prebuild(self, env, srcdir):
        host_builddir = self._host_builddir(srcdir)
        os.makedirs(host_builddir)

        host_env = env.copy()
        host_env.update(
            {
                "AR": "/usr/bin/ar",
                "CC": "/usr/bin/cc",
                "CFLAGS": "-O2",
                "CPP": "/usr/bin/cc -E",
                "CPPFLAGS": "",
                "CXX": "/usr/bin/c++",
                "CXXFLAGS": "-O2",
                "LD": "/usr/bin/cc",
                "LDFLAGS": "",
                "RANLIB": "/usr/bin/ranlib",
            }
        )
        host_env.pop("CONFIG_SITE", None)
        host_env.pop("PKG_CONFIG_LIBDIR", None)
        host_env.pop("PKG_CONFIG_PATH", None)
        host_env.pop("PKG_CONFIG_SYSROOT_DIR", None)
        steps.cmd(
            [
                os.path.join(srcdir, "configure"),
                "--prefix=/usr",
                "--disable-test-modules",
                "--without-ensurepip",
            ],
            cwd=host_builddir,
            env=host_env,
        )
        steps.cmd(
            [
                env["MAKE"],
                env["MAKEFLAGS"],
                "BUILDPYTHON=python-host",
                "python-host",
            ],
            cwd=host_builddir,
            env=host_env,
        )

    def configure(self, env, srcdir):
        host_env = env.copy()
        host_env["CC"] = "/usr/bin/cc"
        build_triplet = steps.cmd_output(
            [os.path.join(srcdir, "config.guess")],
            cwd=srcdir,
            env=host_env,
            text=True,
        ).strip()

        env["ac_cv_aligned_required"] = "no"
        env["ac_cv_file__dev_ptc"] = "no"
        env["ac_cv_file__dev_ptmx"] = "yes"
        env["ac_cv_func_pthread_getcpuclockid"] = "no"
        # Readline's pkg-config file names a generic termcap provider, while
        # Pedigree ships ncurses' split wide-character libraries.
        env["LIBREADLINE_CFLAGS"] = env["CPPFLAGS"]
        env["LIBREADLINE_LIBS"] = "-lreadline -lncursesw -ltinfow"
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                "--build=%s" % build_triplet,
                "--with-build-python=%s" % self._host_python(srcdir),
                "--enable-shared",
                "--disable-ipv6",
                "--disable-test-modules",
                "--without-mimalloc",
                "--without-ensurepip",
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env["DESTDIR"] = deploydir
        steps.make(srcdir, env, target="install", inplace=False)

    def postdeploy(self, env, srcdir, deploydir):
        self._sanitize_development_metadata(env, srcdir, deploydir)

        bindir = os.path.join(deploydir, "usr", "bin")
        python_link = os.path.join(bindir, "python")
        if os.path.lexists(python_link):
            os.unlink(python_link)
        os.symlink("python3", python_link)

    def _sanitize_development_metadata(self, env, srcdir, deploydir):
        python_version = ".".join(self.version().split(".")[:2])
        python_dir = os.path.join(
            deploydir, "usr", "lib", "python%s" % python_version
        )
        metadata = []
        for filename in os.listdir(python_dir):
            if filename == "build-details.json" or (
                filename.startswith("_sysconfigdata_")
                and filename.endswith(".py")
            ) or (
                filename.startswith("_sysconfig_vars_")
                and filename.endswith(".json")
            ):
                metadata.append(os.path.join(python_dir, filename))
            elif filename.startswith("config-"):
                makefile = os.path.join(python_dir, filename, "Makefile")
                if os.path.isfile(makefile):
                    metadata.append(makefile)

        if not metadata:
            raise RuntimeError("CPython development metadata was not installed")

        makefile = next(
            (path for path in metadata if path.endswith("Makefile")), None
        )
        if makefile is None:
            raise RuntimeError("CPython config Makefile was not installed")
        config_dir = os.path.dirname(makefile)
        target_config_dir = "/" + os.path.relpath(config_dir, deploydir)
        target_include_dir = "/usr/include/python%s" % python_version

        tool_commands = {
            "CROSS_AR": "ar",
            "CROSS_AS": "as",
            "CROSS_CC": "gcc",
            "CROSS_CPP": "cpp",
            "CROSS_CXX": "g++",
            "CROSS_LD": "ld",
            "CROSS_RANLIB": "ranlib",
            "CROSS_STRIP": "strip",
        }
        replacements = [
            (env[key], command)
            for key, command in tool_commands.items()
            if env.get(key)
        ]

        if srcdir:
            builddir = os.path.join(srcdir, "pedigree-build")
            replacements.extend(
                (
                    (self._host_python(srcdir), "python3"),
                    (os.path.join(srcdir, "Include"), target_include_dir),
                    (builddir, target_config_dir),
                    (srcdir, target_config_dir),
                )
            )

        ports_sysroot = os.path.normpath(env["PORTS_SYSROOT"])
        staged_include = os.path.join(ports_sysroot, "usr", "include")
        staged_lib = os.path.join(ports_sysroot, "usr", "lib")
        staged_flags = (
            "-Wl,-rpath-link,%s" % staged_lib,
            "-I%s" % staged_include,
            "-L%s" % staged_lib,
        )
        build_home = env.get("HOME")
        build_userbases = tuple(
            path
            for path in (
                env.get("PYTHONUSERBASE"),
                os.path.join(build_home, ".local")
                if build_home
                else None,
                os.path.join(
                    build_home, "Library", "Python", python_version
                )
                if build_home
                else None,
            )
            if path
        )

        for path in metadata:
            with open(path, encoding="utf-8") as metadata_file:
                contents = metadata_file.read()
            sanitized = contents
            # CPython computes this using the build host, then replaces it at
            # runtime. Do not preserve the builder's home in target metadata.
            sanitized = re.sub(
                r'''(["']userbase["']\s*:\s*)(["'])(?:\\.|(?!\2).)*\2''',
                r'\1""',
                sanitized,
            )
            for flag in staged_flags:
                pattern = re.compile(
                    r"(^|[\s'\"=:])%s(?=$|[\s'\"\\])"
                    % re.escape(flag),
                    re.MULTILINE,
                )
                sanitized = pattern.sub(r"\1", sanitized)
            for source, command in replacements:
                sanitized = sanitized.replace(source, command)
            sanitized = sanitized.replace(ports_sysroot, "")

            forbidden_paths = tuple(
                value
                for value in (
                    env.get("APPS_BASE"),
                    env.get("BUILD_BASE"),
                    env.get("CROSS_BASE"),
                    ports_sysroot,
                    srcdir,
                )
                if value
            ) + build_userbases
            leaked = [value for value in forbidden_paths if value in sanitized]
            if leaked:
                raise RuntimeError(
                    "CPython development metadata contains build paths in "
                    "%s: %s" % (path, ", ".join(leaked))
                )
            if sanitized != contents:
                with open(path, "w", encoding="utf-8") as metadata_file:
                    metadata_file.write(sanitized)
