import pathlib
import shutil

from support import buildsystem
from support import steps


class VimPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return "vim"

    def version(self):
        return "9.2.1031"

    def build_requires(self):
        return ["ncurses"]

    def install_deps(self):
        return ["ncurses", "perl"]

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://github.com/vim/vim/archive/refs/tags/"
            "v%s.tar.gz" % self.version(),
            target,
            sha256=(
                "15a2cd025f92593ad6945f906ed0ae93"
                "e89b716da99633f80e95b4b6b7bf73dd"
            ),
        )

    def configure(self, env, srcdir):
        env.update(
            {
                "vim_cv_getcwd_broken": "no",
                "vim_cv_memmove_handles_overlap": "yes",
                "vim_cv_stat_ignores_slash": "yes",
                "vim_cv_tgetent": "zero",
                "vim_cv_timer_create": "no",
                "vim_cv_timer_create_with_lrt": "no",
                "vim_cv_terminfo": "yes",
                "vim_cv_toupper_broken": "no",
                "vim_cv_uname_m_output": "x86_64",
                "vim_cv_uname_output": "Pedigree",
                "vim_cv_uname_r_output": "1",
            }
        )
        steps.run_configure(
            self,
            srcdir,
            env,
            extra_config=(
                "--disable-acl",
                "--disable-channel",
                "--disable-gui",
                "--disable-netbeans",
                "--disable-nls",
                "--disable-selinux",
                "--disable-xattr",
                "--disable-xsmp",
                "--enable-gpm=no",
                "--enable-multibyte",
                "--with-features=normal",
                "--with-tlib=tinfow",
                "--without-x",
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env["DESTDIR"] = deploydir
        steps.make(srcdir, env, target="install")

    def postdeploy(self, env, srcdir, deploydir):
        for tools_dir in pathlib.Path(deploydir).glob("usr/share/vim/vim*/tools"):
            shutil.rmtree(tools_dir)
