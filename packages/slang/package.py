from support import buildsystem
from support import steps


class SlangPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = "bz2"

    def name(self):
        return "slang"

    def version(self):
        return "2.3.3"

    def build_requires(self):
        return ["ncurses"]

    def install_deps(self):
        # S-Lang reads the target terminfo database directly.
        return ["ncurses"]

    def patches(self, env, srcdir):
        return ["pedigree-target.diff"]

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://www.jedsoft.org/releases/slang/slang-%s.tar.bz2"
            % self.version(),
            target,
            sha256=(
                "f9145054ae131973c61208ea82486d5d"
                "d10e3c5cdad23b7c4a0617743c8f5a18"
            ),
        )

    def configure(self, env, srcdir):
        env["ac_cv_func_cfgetospeed"] = "no"
        env["ac_cv_func_isinf"] = "yes"
        env["ac_cv_func_isnan"] = "yes"
        env["ac_cv_func_issetugid"] = "no"
        env["ac_cv_func_pathconf"] = "no"
        env["ac_cv_path_nc5config"] = "no"
        steps.run_configure(
            self,
            srcdir,
            env,
            not_paths=("infodir",),
            extra_config=(
                "--with-readline=slang",
                "--with-terminfo=default",
                "--without-iconv",
                "--without-onig",
                "--without-pcre",
                "--without-png",
                "--without-x",
                "--without-z",
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.make(
            srcdir,
            env,
            target="install",
            extra_opts=("DESTDIR=%s" % deploydir,),
            parallel=False,
        )
