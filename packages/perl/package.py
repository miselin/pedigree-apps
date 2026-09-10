import os
import shutil
import stat

from support import buildsystem
from support import steps


class PerlPackage(buildsystem.Package):

    PERL_CROSS_COMMIT = "c2d8f8b7027ed20cd982c9f2c091463510b89f33"
    PERL_CROSS_SHA256 = (
        "93cc5d8eb85d61580803d7eaa2001422"
        "4fbb188db17444ba528eb702412f6445"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = "xz"

    def name(self):
        return "perl"

    def version(self):
        return "5.44.0"

    def release_version(self):
        # PUP releases are immutable; this numeric revision avoids replacing
        # the older package while remaining newer under PUP's version order.
        return self.version() + ".1"

    def patches(self, env, srcdir):
        return [
            "errno-cross.diff",
            "bootstrap-writable-dir.diff",
            "pedigree-missing-syscalls.diff",
            "pedigree-thread-signal.diff",
            "pedigree-truncate.diff",
        ]

    def options(self):
        return self._options

    def _host_tool(self, name):
        path = shutil.which(name)
        if not path:
            raise RuntimeError("Perl cross-build requires host %s" % name)
        return path

    def download(self, env, target):
        steps.download(
            "https://www.cpan.org/src/5.0/perl-%s.tar.xz" % self.version(),
            target,
            sha256=(
                "505cf43912e9480495c344c70260452e"
                "32aa2a73c546a026b3f100053b23ce91"
            ),
        )

    def prebuild(self, env, srcdir):
        # The latest perl-cross release predates Perl 5.44 support. Pin the
        # first upstream revision carrying the matching 5.44 patch set.
        archive = os.path.join(
            env["DOWNLOAD_TEMP"],
            "perl-cross-%s.tar.gz" % self.PERL_CROSS_COMMIT,
        )
        steps.download(
            "https://github.com/arsv/perl-cross/archive/%s.tar.gz"
            % self.PERL_CROSS_COMMIT,
            archive,
            sha256=self.PERL_CROSS_SHA256,
        )
        steps.cmd(
            [env["TAR"], "--strip-components=1", "-xf", archive],
            cwd=srcdir,
            env=env,
        )
        shutil.copyfile(
            os.path.join(self._path, "pedigree.hint"),
            os.path.join(srcdir, "cnf", "hints", "pedigree"),
        )

    def configure(self, env, srcdir):
        host_env = env.copy()
        host_env.update(
            {
                "HOSTAR": self._host_tool("ar"),
                "HOSTCC": self._host_tool("cc"),
                "HOSTCFLAGS": "-O2",
                "HOSTLDFLAGS": "",
                "HOSTNM": self._host_tool("nm"),
                "HOSTOBJDUMP": self._host_tool("objdump"),
                "HOSTRANLIB": self._host_tool("ranlib"),
                "HOSTREADELF": self._host_tool("readelf"),
            }
        )
        build_triplet = steps.cmd_output(
            [os.path.join(srcdir, "cnf", "config.guess")],
            cwd=srcdir,
            env=host_env,
            text=True,
        ).strip()
        tool_prefix = os.path.join(
            env["CROSS_BASE"], "bin", env["CROSS_TARGET"] + "-"
        )
        steps.cmd(
            [
                os.path.join(srcdir, "configure"),
                "--mode=cross",
                "--build=%s" % build_triplet,
                "--target=%s" % env["CROSS_TARGET"],
                "--target-tools-prefix=%s" % tool_prefix,
                "--sysroot=%s" % env["TARGET_SYSROOT"],
                "--prefix=/usr",
                "--man1dir=/usr/share/man/man1",
                "--man3dir=/usr/share/man/man3",
                "-Dosname=pedigree",
                "-Duseshrplib",
                "-Dusethreads",
                "-Duse64bitall",
                "-Dusedl",
                "-Dinc_version_list=none",
                # perl-cross uses the GNU feature profile for its prototype
                # probes. Compile Perl with the same declarations so working
                # musl interfaces such as eaccess(3) are not misdetected.
                "-Accflags=-D_GNU_SOURCE",
            ],
            cwd=srcdir,
            env=host_env,
        )

    def build(self, env, srcdir):
        # Perl's bootstrap mutates the shared lib/ tree while building core
        # extensions; parallel MakeMaker jobs can race its permission check.
        steps.make(srcdir, env, parallel=False)

    def deploy(self, env, srcdir, deploydir):
        steps.make(
            srcdir,
            env,
            target="install",
            parallel=False,
            extra_opts=("DESTDIR=%s" % deploydir,),
        )

    def postdeploy(self, env, srcdir, deploydir):
        archlib = os.path.join(
            deploydir,
            "usr",
            "lib",
            "perl5",
            self.version(),
            env["CROSS_TARGET"],
        )
        metadata = (
            os.path.join(archlib, "Config.pm"),
            os.path.join(archlib, "Config_heavy.pl"),
            os.path.join(archlib, "CORE", "config.h"),
        )
        missing = [path for path in metadata if not os.path.isfile(path)]
        if missing:
            raise RuntimeError(
                "Perl development metadata was not installed: %s"
                % ", ".join(missing)
            )

        cross_base = os.path.normpath(env["CROSS_BASE"])
        target_sysroot = os.path.normpath(env["TARGET_SYSROOT"])
        ports_sysroot = os.path.normpath(env["PORTS_SYSROOT"])
        tool_prefix = os.path.join(
            cross_base, "bin", env["CROSS_TARGET"] + "-"
        )
        native_tools = (
            "ar",
            "gcc",
            "nm",
            "objdump",
            "ranlib",
            "readelf",
        )
        build_only_options = (
            "--sysroot=%s" % target_sysroot,
            "--target-tools-prefix=%s" % tool_prefix,
        )
        forbidden_paths = tuple(
            path
            for path in (
                env.get("APPS_BASE"),
                cross_base,
                target_sysroot,
                ports_sysroot,
            )
            if path
        )

        for path in metadata:
            with open(path, encoding="utf-8") as source:
                contents = source.read()
            sanitized = contents
            for tool in native_tools:
                sanitized = sanitized.replace(tool_prefix + tool, tool)
            for option in build_only_options:
                sanitized = sanitized.replace(option, "")
            # Dependency include and library paths remain meaningful on the
            # target once rebased from the transient package sysroot.
            sanitized = sanitized.replace(ports_sysroot, "")
            sanitized = sanitized.replace(target_sysroot, "")

            leaked = [path for path in forbidden_paths if path in sanitized]
            if leaked:
                raise RuntimeError(
                    "Perl development metadata contains build paths in %s: %s"
                    % (path, ", ".join(leaked))
                )
            if sanitized != contents:
                original_mode = stat.S_IMODE(os.stat(path).st_mode)
                os.chmod(path, original_mode | stat.S_IWUSR)
                try:
                    with open(path, "w", encoding="utf-8") as destination:
                        destination.write(sanitized)
                finally:
                    os.chmod(path, original_mode)
