import os

from support import buildsystem
from support import steps


SOURCE_VERSION = "2.32.10"
PORT_PROFILE = "static-offscreen"


class Sdl2Package(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return "sdl2"

    def version(self):
        return SOURCE_VERSION

    def build_requires(self):
        return []

    def install_deps(self):
        # sdl2-config uses sed for option and static-link flag handling.
        return ["sed"]

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://www.libsdl.org/release/SDL2-%s.tar.gz"
            % SOURCE_VERSION,
            target,
            sha256=(
                "5f5993c530f084535c65a6879e9b26ad"
                "441169b3e25d789d83287040a9ca5165"
            ),
        )

    def configure(self, env, srcdir):
        # Pedigree does not yet export a packaged display or audio frontend.
        # Keep the portable SDL core usable without claiming Linux devices.
        # CMake does not read config.site, so cache libc symbols whose backing
        # functionality is unavailable.
        steps.cmake_configure(
            self,
            srcdir,
            env,
            extra_config=(
                "-DSDL_SHARED=OFF",
                "-DSDL_STATIC=ON",
                "-DSDL_STATIC_PIC=ON",
                "-DSDL_TEST=OFF",
                "-DSDL_TESTS=OFF",
                "-DSDL_INSTALL_TESTS=OFF",
                "-DSDL2_DISABLE_SDL2MAIN=ON",
                "-DSDL_ASSEMBLY=OFF",
                "-DSDL_RPATH=OFF",
                "-DSDL_DISKAUDIO=OFF",
                "-DSDL_DUMMYAUDIO=ON",
                "-DSDL_DUMMYVIDEO=ON",
                "-DSDL_OFFSCREEN=ON",
                "-DSDL_OPENGL=OFF",
                "-DSDL_OPENGLES=OFF",
                "-DSDL_VULKAN=OFF",
                "-DSDL_X11=OFF",
                "-DSDL_WAYLAND=OFF",
                "-DSDL_KMSDRM=OFF",
                "-DSDL_DIRECTFB=OFF",
                "-DSDL_RPI=OFF",
                "-DSDL_VIVANTE=OFF",
                "-DSDL_ALSA=OFF",
                "-DSDL_JACK=OFF",
                "-DSDL_PIPEWIRE=OFF",
                "-DSDL_PULSEAUDIO=OFF",
                "-DSDL_ESD=OFF",
                "-DSDL_ARTS=OFF",
                "-DSDL_NAS=OFF",
                "-DSDL_SNDIO=OFF",
                "-DSDL_OSS=OFF",
                "-DSDL_FUSIONSOUND=OFF",
                "-DSDL_LIBSAMPLERATE=OFF",
                "-DSDL_HIDAPI=OFF",
                "-DSDL_JOYSTICK=OFF",
                "-DSDL_HAPTIC=OFF",
                "-DSDL_SENSOR=OFF",
                "-DSDL_POWER=OFF",
                "-DSDL_LIBUDEV=OFF",
                "-DSDL_DBUS=OFF",
                "-DSDL_IBUS=OFF",
                "-DSDL_RENDER=ON",
                "-DSDL_THREADS=ON",
                "-DSDL_PTHREADS=ON",
                "-DSDL_TIMERS=ON",
                "-DSDL_LOADSO=ON",
                "-DSDL_FILESYSTEM=ON",
                "-DSDL_LOCALE=ON",
                "-DSDL_MISC=ON",
            ),
        )

    def build(self, env, srcdir):
        steps.cmake_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.cmake_install(srcdir, env, deploydir)

    def postdeploy(self, env, srcdir, deploydir):
        required = (
            os.path.join("usr", "bin", "sdl2-config"),
            os.path.join("usr", "include", "SDL2", "SDL_config.h"),
            os.path.join("usr", "lib", "libSDL2.a"),
            os.path.join("usr", "lib", "pkgconfig", "sdl2.pc"),
        )
        missing = [
            relative
            for relative in required
            if not os.path.isfile(os.path.join(deploydir, relative))
        ]
        if missing:
            raise RuntimeError(
                "SDL2 static compatibility files were not installed: %s"
                % ", ".join(missing)
            )

        config_path = os.path.join(
            deploydir, "usr", "include", "SDL2", "SDL_config.h"
        )
        with open(config_path, encoding="utf-8") as config_file:
            config = config_file.read()
        required_features = (
            "#define SDL_AUDIO_DRIVER_DUMMY 1",
            "#define SDL_VIDEO_DRIVER_DUMMY 1",
            "#define SDL_VIDEO_DRIVER_OFFSCREEN 1",
            "#define SDL_THREAD_PTHREAD 1",
            "#define SDL_TIMER_UNIX 1",
            "#define SDL_LOADSO_DLOPEN 1",
            "#define SDL_FILESYSTEM_UNIX 1",
        )
        missing_features = [
            feature for feature in required_features if feature not in config
        ]
        if missing_features:
            raise RuntimeError(
                "SDL2 compatibility profile is incomplete: %s"
                % ", ".join(missing_features)
            )

        forbidden_features = (
            "#define SDL_AUDIO_DRIVER_ALSA 1",
            "#define SDL_AUDIO_DRIVER_PIPEWIRE 1",
            "#define SDL_AUDIO_DRIVER_PULSEAUDIO 1",
            "#define SDL_VIDEO_DRIVER_KMSDRM 1",
            "#define SDL_VIDEO_DRIVER_WAYLAND 1",
            "#define SDL_VIDEO_DRIVER_X11 1",
        )
        enabled_host_features = [
            feature for feature in forbidden_features if feature in config
        ]
        if enabled_host_features:
            raise RuntimeError(
                "SDL2 compatibility profile enabled unsupported host drivers: %s"
                % ", ".join(enabled_host_features)
            )
