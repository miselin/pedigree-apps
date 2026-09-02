import os

from support import buildsystem
from support import steps


class LibtoolPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibtoolPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'libtool'

    def version(self):
        return '2.6.2'

    def patches(self, env, srcdir):
        return ['pedigree-elf.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='2ef1067c16c97db930fd740cc9bc3d3ba9a583804ae5ac42cc3e8719e49e191e')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--disable-shared', '--enable-static',
            '--enable-cross-guesses=conservative'))

    def build(self, env, srcdir):
        # Patching the installed target macro makes it newer than the release
        # tarball's generated files. Keep those release outputs authoritative;
        # the builder's Automake need not match upstream's exact version.
        steps.make(
            srcdir,
            env,
            extra_opts=(
                'ACLOCAL=true',
                'AUTOCONF=true',
                'AUTOHEADER=true',
                'AUTOMAKE=true',
            ),
        )

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(
            srcdir,
            env,
            'install',
            extra_opts=(
                'ACLOCAL=true',
                'AUTOCONF=true',
                'AUTOHEADER=true',
                'AUTOMAKE=true',
            ),
        )

    def postdeploy(self, env, srcdir, deploydir):
        # The preloaded dlopen backend is already folded into libltdl.a.
        # Keeping its convenience archive paths would make the installed
        # metadata point back into the transient build tree.
        metadata = os.path.join(deploydir, "usr", "lib", "libltdl.la")
        with open(metadata, encoding="utf-8") as source:
            lines = source.readlines()
        metadata_content = "".join(
            "dependency_libs=''\n"
            if line.startswith("dependency_libs=")
            else line
            for line in lines
        )

        # The installed driver will run on Pedigree, so express its compiler
        # and sysroot paths in the target FHS rather than the cross builder.
        driver = os.path.join(deploydir, "usr", "bin", "libtool")
        with open(driver, encoding="utf-8") as source:
            content = source.read()

        sanitized = content
        native_tools = (
            ("CROSS_CC", "gcc"),
            ("CROSS_CXX", "g++"),
            ("CROSS_CPP", "cpp"),
            ("CROSS_AS", "as"),
            ("CROSS_LD", "ld"),
            ("CROSS_AR", "ar"),
            ("CROSS_RANLIB", "ranlib"),
            ("CROSS_STRIP", "strip"),
        )
        for variable, native_tool in native_tools:
            cross_tool = env.get(variable)
            if cross_tool:
                sanitized = sanitized.replace(cross_tool, native_tool)

        tool_prefix = os.path.join(
            env["CROSS_BASE"], "bin", env["CROSS_TARGET"] + "-"
        )
        for native_tool in (
            "ar",
            "as",
            "cpp",
            "g++",
            "gcc",
            "ld",
            "nm",
            "objdump",
            "ranlib",
            "readelf",
            "strip",
        ):
            sanitized = sanitized.replace(tool_prefix + native_tool, native_tool)
            sanitized = sanitized.replace(
                env["CROSS_TARGET"] + "-" + native_tool,
                native_tool,
            )

        ports_sysroot = os.path.normpath(env["PORTS_SYSROOT"])
        target_sysroot = os.path.normpath(env["TARGET_SYSROOT"])
        cross_base = os.path.normpath(env["CROSS_BASE"])
        for source, target in (
            (ports_sysroot, ""),
            (target_sysroot, "/usr"),
            (cross_base, "/usr"),
        ):
            sanitized = sanitized.replace(source, target)

        forbidden_paths = tuple(
            path
            for path in (
                env.get("APPS_BASE"),
                env.get("BUILD_BASE"),
                env.get("OUTPUT_BASE"),
                env.get("DOWNLOAD_TEMP"),
                cross_base,
                target_sysroot,
                ports_sysroot,
                srcdir,
            )
            if path
        )
        for path, candidate in (
            (metadata, metadata_content),
            (driver, sanitized),
        ):
            leaked = [value for value in forbidden_paths if value in candidate]
            if leaked:
                raise RuntimeError(
                    "Libtool metadata contains cross-build paths in %s: %s"
                    % (path, ", ".join(leaked))
                )

        with open(metadata, "w", encoding="utf-8") as destination:
            destination.write(metadata_content)
        with open(driver, "w", encoding="utf-8") as destination:
            destination.write(sanitized)
