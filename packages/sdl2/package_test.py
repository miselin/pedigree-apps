import os
import tempfile
import unittest
from unittest import mock

from .package import PORT_PROFILE, SOURCE_VERSION, Sdl2Package


class Sdl2PackageTest(unittest.TestCase):

    def setUp(self):
        self.package = Sdl2Package(__file__)

    @mock.patch("packages.sdl2.package.steps.download")
    def test_download_is_current_official_release_and_digest_pinned(
        self, download
    ):
        self.package.download({}, "/download")

        self.assertEqual(SOURCE_VERSION, "2.32.10")
        self.assertEqual(PORT_PROFILE, "static-offscreen")
        self.assertEqual(
            download.call_args.args[0],
            "https://www.libsdl.org/release/SDL2-2.32.10.tar.gz",
        )
        self.assertEqual(
            download.call_args.kwargs["sha256"],
            "5f5993c530f084535c65a6879e9b26ad441169b3e25d789d83287040a9ca5165",
        )

    @mock.patch("packages.sdl2.package.steps.cmake_configure")
    def test_configure_is_static_and_does_not_claim_host_drivers(
        self, configure
    ):
        self.package.configure({}, "/source")

        options = configure.call_args.kwargs["extra_config"]
        for option in (
            "-DSDL_SHARED=OFF",
            "-DSDL_STATIC=ON",
            "-DSDL_STATIC_PIC=ON",
            "-DSDL_DUMMYAUDIO=ON",
            "-DSDL_DUMMYVIDEO=ON",
            "-DSDL_OFFSCREEN=ON",
            "-DSDL_THREADS=ON",
            "-DSDL_PTHREADS=ON",
            "-DSDL_TIMERS=ON",
            "-DSDL_LOADSO=ON",
            "-DSDL_FILESYSTEM=ON",
        ):
            self.assertIn(option, options)
        self.assertNotIn("-DHAVE_SYS_INOTIFY_H=OFF", options)
        for option in (
            "-DSDL_X11=OFF",
            "-DSDL_WAYLAND=OFF",
            "-DSDL_KMSDRM=OFF",
            "-DSDL_ALSA=OFF",
            "-DSDL_PIPEWIRE=OFF",
            "-DSDL_PULSEAUDIO=OFF",
            "-DSDL_LIBUDEV=OFF",
            "-DSDL_DBUS=OFF",
            "-DSDL_HIDAPI=OFF",
        ):
            self.assertIn(option, options)

    def test_profile_declares_its_config_script_dependency(self):
        self.assertEqual(self.package.build_requires(), [])
        self.assertEqual(self.package.install_deps(), ["sed"])

    def test_postdeploy_requires_static_offscreen_profile(self):
        with tempfile.TemporaryDirectory() as deploydir:
            paths = (
                os.path.join("usr", "bin", "sdl2-config"),
                os.path.join("usr", "lib", "libSDL2.a"),
                os.path.join("usr", "lib", "pkgconfig", "sdl2.pc"),
            )
            for relative in paths:
                path = os.path.join(deploydir, relative)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb"):
                    pass

            config_path = os.path.join(
                deploydir, "usr", "include", "SDL2", "SDL_config.h"
            )
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as config:
                config.write(
                    "\n".join(
                        (
                            "#define SDL_AUDIO_DRIVER_DUMMY 1",
                            "#define SDL_VIDEO_DRIVER_DUMMY 1",
                            "#define SDL_VIDEO_DRIVER_OFFSCREEN 1",
                            "#define SDL_THREAD_PTHREAD 1",
                            "#define SDL_TIMER_UNIX 1",
                            "#define SDL_LOADSO_DLOPEN 1",
                            "#define SDL_FILESYSTEM_UNIX 1",
                        )
                    )
                )

            self.package.postdeploy({}, "/source", deploydir)

    def test_postdeploy_rejects_host_video_driver(self):
        with tempfile.TemporaryDirectory() as deploydir:
            paths = (
                os.path.join("usr", "bin", "sdl2-config"),
                os.path.join("usr", "lib", "libSDL2.a"),
                os.path.join("usr", "lib", "pkgconfig", "sdl2.pc"),
            )
            for relative in paths:
                path = os.path.join(deploydir, relative)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb"):
                    pass

            config_path = os.path.join(
                deploydir, "usr", "include", "SDL2", "SDL_config.h"
            )
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as config:
                config.write(
                    "\n".join(
                        (
                            "#define SDL_AUDIO_DRIVER_DUMMY 1",
                            "#define SDL_VIDEO_DRIVER_DUMMY 1",
                            "#define SDL_VIDEO_DRIVER_OFFSCREEN 1",
                            "#define SDL_THREAD_PTHREAD 1",
                            "#define SDL_TIMER_UNIX 1",
                            "#define SDL_LOADSO_DLOPEN 1",
                            "#define SDL_FILESYSTEM_UNIX 1",
                            "#define SDL_VIDEO_DRIVER_X11 1",
                        )
                    )
                )

            with self.assertRaisesRegex(
                RuntimeError, "unsupported host drivers"
            ):
                self.package.postdeploy({}, "/source", deploydir)


if __name__ == "__main__":
    unittest.main()
