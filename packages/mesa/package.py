import os

from support import buildsystem
from support import steps


class MesaPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = "xz"

    def name(self):
        return "mesa"

    def version(self):
        # Mesa 25.1 removed OSMesa. Pedigree's current framebuffer graphics
        # stack still consumes that API, so 25.0.7 is the newest compatible
        # release rather than an arbitrary historical pin.
        return "25.0.7"

    def build_requires(self):
        return []

    def install_deps(self):
        return []

    def patches(self, env, srcdir):
        return ["pedigree-platform.diff"]

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://archive.mesa3d.org/mesa-%s.tar.xz" % self.version(),
            target,
            sha256=(
                "592272df3cf01e85e7db300c449df506"
                "1092574d099da275d19e97ef0510f8a6"
            ),
        )

    def configure(self, env, srcdir):
        steps.meson_configure(
            self,
            srcdir,
            env,
            extra_config=(
                # OSMesa is a shared_library() target in this release.
                "-Ddefault_library=shared",
                "-Dplatforms=",
                "-Dgallium-drivers=softpipe",
                "-Dvulkan-drivers=",
                "-Dosmesa=true",
                "-Dopengl=true",
                "-Dgles1=disabled",
                "-Dgles2=disabled",
                "-Dglx=disabled",
                "-Degl=disabled",
                "-Dgbm=disabled",
                "-Dllvm=disabled",
                "-Dshared-llvm=disabled",
                "-Dgallium-vdpau=disabled",
                "-Dgallium-va=disabled",
                "-Dgallium-xa=disabled",
                "-Dgallium-nine=false",
                "-Dgallium-opencl=disabled",
                "-Dgallium-rusticl=false",
                "-Dshader-cache=disabled",
                "-Dxmlconfig=disabled",
                "-Dexpat=disabled",
                "-Dzlib=disabled",
                "-Dzstd=disabled",
                "-Dvalgrind=disabled",
                "-Dlibunwind=disabled",
                "-Dlmsensors=disabled",
                "-Dbuild-tests=false",
                "-Dtools=",
                "-Dvideo-codecs=",
                "-Dperfetto=false",
                "-Dallow-kcmp=disabled",
            ),
        )

    def build(self, env, srcdir):
        steps.meson_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.meson_install(srcdir, env, deploydir)

    def postdeploy(self, env, srcdir, deploydir):
        libdir = os.path.join(deploydir, "usr", "lib")
        required_files = (
            os.path.join(deploydir, "usr", "include", "GL", "osmesa.h"),
            os.path.join(libdir, "libOSMesa.so.8.0.0"),
            os.path.join(libdir, "pkgconfig", "osmesa.pc"),
        )
        missing = [path for path in required_files if not os.path.isfile(path)]
        if missing:
            raise RuntimeError(
                "Mesa OSMesa shared profile is incomplete: %s"
                % ", ".join(missing)
            )

        for link_name, target in (
            ("libOSMesa.so.8", "libOSMesa.so.8.0.0"),
            ("libOSMesa.so", "libOSMesa.so.8"),
        ):
            link_path = os.path.join(libdir, link_name)
            if not os.path.islink(link_path) or os.readlink(link_path) != target:
                raise RuntimeError(
                    "Mesa OSMesa shared ABI link is invalid: %s" % link_path
                )

        static_library = os.path.join(libdir, "libOSMesa.a")
        if os.path.lexists(static_library):
            raise RuntimeError(
                "Mesa OSMesa unexpectedly installed a static library: %s"
                % static_library
            )
