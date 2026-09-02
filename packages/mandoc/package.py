import os
import shlex

from support import buildsystem
from support import steps


class MandocPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return "mandoc"

    def version(self):
        return "1.14.6"

    def build_requires(self):
        return ["zlib"]

    def install_deps(self):
        return ["less", "zlib"]

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://mandoc.bsd.lv/snapshots/mandoc-%s.tar.gz"
            % self.version(),
            target,
            sha256=(
                "8bf0d570f01e70a6e124884088870cbe"
                "d7537f36328d512909eb10cd53179d9c"
            ),
        )

    def prebuild(self, env, srcdir):
        # mandoc's configure script runs every feature probe. Supply the
        # conservative target answers explicitly so no Pedigree executable is
        # mistaken for a runnable build-host probe.
        values = {
            "AR": env["CROSS_AR"],
            "BINDIR": "/usr/bin",
            "BINM_APROPOS": "mandoc-apropos",
            "BINM_MAKEWHATIS": "mandocdb",
            "BINM_MAN": "mandoc-man",
            "BINM_PAGER": "/usr/bin/less",
            "BINM_SOELIM": "mandoc-soelim",
            "BINM_WHATIS": "mandoc-whatis",
            "BUILD_CATMAN": "0",
            "BUILD_CGI": "0",
            "CC": env["CROSS_CC"],
            "CFLAGS": "%s %s"
            % (env.get("CFLAGS", ""), env.get("CPPFLAGS", "")),
            "HAVE_ATTRIBUTE": "1",
            "HAVE_CMSG": "0",
            "HAVE_DIRENT_NAMLEN": "0",
            "HAVE_EFTYPE": "0",
            "HAVE_ENDIAN": "1",
            "HAVE_ERR": "1",
            "HAVE_FTS": "0",
            "HAVE_FTS_COMPARE_CONST": "0",
            "HAVE_GETLINE": "1",
            "HAVE_GETSUBOPT": "1",
            "HAVE_ISBLANK": "1",
            "HAVE_LESS_T": "0",
            "HAVE_MKDTEMP": "1",
            "HAVE_MKSTEMPS": "1",
            "HAVE_NANOSLEEP": "1",
            "HAVE_NTOHL": "1",
            "HAVE_O_DIRECTORY": "1",
            "HAVE_OHASH": "0",
            "HAVE_PATH_MAX": "1",
            "HAVE_PLEDGE": "0",
            "HAVE_PROGNAME": "0",
            "HAVE_REALLOCARRAY": "1",
            "HAVE_RECALLOCARRAY": "0",
            "HAVE_RECVMSG": "0",
            "HAVE_REWB_BSD": "0",
            "HAVE_REWB_SYSV": "0",
            "HAVE_SANDBOX_INIT": "0",
            "HAVE_STATIC": "0",
            "HAVE_STRCASESTR": "1",
            "HAVE_STRINGLIST": "0",
            "HAVE_STRLCAT": "1",
            "HAVE_STRLCPY": "1",
            "HAVE_STRNDUP": "1",
            "HAVE_STRPTIME": "1",
            "HAVE_STRSEP": "1",
            "HAVE_STRTONUM": "0",
            "HAVE_SYS_ENDIAN": "0",
            "HAVE_VASPRINTF": "1",
            "HAVE_WCHAR": "0",
            "HAVE_WFLAG": "0",
            "INSTALL_LIBMANDOC": "0",
            "LDFLAGS": env.get("LDFLAGS", ""),
            "LN": "ln -sf",
            "MANDIR": "/usr/share/man",
            "MANM_EQN": "mandoc_eqn",
            "MANM_MAN": "mandoc_man",
            "MANM_MANCONF": "mandoc.conf",
            "MANM_MDOC": "mandoc_mdoc",
            "MANM_ROFF": "mandoc_roff",
            "MANM_TBL": "mandoc_tbl",
            "MANPATH_BASE": "/usr/share/man",
            "MANPATH_DEFAULT": "/usr/share/man",
            "NEED_GNU_SOURCE": "1",
            "OSENUM": "MANDOC_OS_OTHER",
            "OSNAME": "Pedigree",
            "PREFIX": "/usr",
            "SBINDIR": "/usr/sbin",
        }
        with open(
            os.path.join(srcdir, "configure.local"),
            "w",
            encoding="utf-8",
        ) as config:
            for key, value in values.items():
                config.write("%s=%s\n" % (key, shlex.quote(value.strip())))

    def configure(self, env, srcdir):
        steps.cmd(
            [os.path.join(srcdir, "configure")],
            cwd=srcdir,
            env=env,
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
        formatter = os.path.join(deploydir, "usr", "bin", "mandoc")
        conflicting_man = os.path.join(deploydir, "usr", "bin", "man")
        if not os.path.isfile(formatter):
            raise RuntimeError("mandoc formatter was not installed")
        if os.path.lexists(conflicting_man):
            raise RuntimeError("formatter package unexpectedly installed man")
