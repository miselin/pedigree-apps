import os

from support import buildsystem
from support import steps


class ManDbPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = "xz"

    def name(self):
        return "man-db"

    def version(self):
        return "2.13.1"

    def build_requires(self):
        return ["gdbm", "libpipeline", "mandoc", "zlib"]

    def install_deps(self):
        return [
            "gdbm",
            "grep",
            "gzip",
            "less",
            "libpipeline",
            "mandoc",
            "zlib",
        ]

    def patches(self, env, srcdir):
        return [
            "gnulib-pselect-stddef.diff",
            "mandoc-default-preprocessor.diff",
        ]

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://download.savannah.nongnu.org/releases/man-db/"
            "man-db-%s.tar.xz" % self.version(),
            target,
            sha256=(
                "8afebb6f7eb6bb8542929458841f5c7e"
                "6f240e30c86358c1fbcefbea076c87d9"
            ),
        )

    def configure(self, env, srcdir):
        # The formatter is a target executable and cannot be probed by the
        # build host. These values describe mandoc's supported invocation.
        env["man_cv_prog_gnu_nroff"] = "no"
        env["man_cv_prog_heirloom_nroff"] = "no"
        env["man_cv_prog_nroff_macro"] = "-mandoc"
        env["man_cv_prog_nroff_warnings"] = "no"
        env["ac_cv_prog_cat"] = "/usr/bin/cat"
        env["ac_cv_prog_grep"] = "/usr/bin/grep"
        env["ac_cv_prog_tr"] = "/usr/bin/tr"
        env["ac_cv_prog_troff"] = ""
        steps.run_configure(
            self,
            srcdir,
            env,
            extra_config=(
                "--with-db=gdbm",
                "--with-config-file=/etc/man_db.conf",
                "--with-nroff=/usr/bin/mandoc",
                "--with-pager=/usr/bin/less",
                "--with-gzip=/usr/bin/gzip",
                "--with-browser=",
                "--with-eqn=",
                "--with-neqn=",
                "--with-tbl=",
                "--with-col=",
                "--with-vgrind=",
                "--with-refer=",
                "--with-grap=",
                "--with-pic=",
                "--with-compress=",
                "--with-bzip2=",
                "--with-xz=",
                "--with-lzma=",
                "--with-lzip=",
                "--with-zstd=",
                "--with-systemdtmpfilesdir=no",
                "--with-systemdsystemunitdir=no",
                "--with-snapdir=/var/lib/snapd/snap",
                "--enable-cross-guesses=conservative",
                "--disable-cache-owner",
                "--disable-dependency-tracking",
                "--disable-manual",
                "--disable-nls",
                "--disable-rpath",
                "--disable-setuid",
                "--disable-shared",
                "--disable-threads",
                "--enable-static",
                "--without-libseccomp",
            ),
        )
        self._disable_libtool_rpaths(env, srcdir)

    @staticmethod
    def _disable_libtool_rpaths(env, srcdir):
        libtool_path = os.path.join(
            steps.get_builddir(srcdir, env, True), "libtool"
        )
        with open(libtool_path, encoding="utf-8") as source:
            contents = source.read()

        replacements = (
            ("hardcode_into_libs=yes", "hardcode_into_libs=no"),
            (
                'hardcode_libdir_flag_spec="\\$wl-rpath \\$wl\\$libdir"',
                'hardcode_libdir_flag_spec=""',
            ),
            ("hardcode_action=immediate", "hardcode_action=unsupported"),
        )
        for old, new in replacements:
            if old not in contents:
                raise RuntimeError(
                    "man-db Libtool is missing setting: %s" % old
                )
            contents = contents.replace(old, new, 1)

        with open(libtool_path, "w", encoding="utf-8") as destination:
            destination.write(contents)

    def build(self, env, srcdir):
        steps.make(srcdir, env, parallel=False)

    def deploy(self, env, srcdir, deploydir):
        steps.make(
            srcdir,
            env,
            target="install",
            extra_opts=("DESTDIR=%s" % deploydir,),
            parallel=False,
        )
