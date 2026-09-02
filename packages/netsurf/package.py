UPSTREAM_VERSION = "3.11"

DISABLED_REASON = (
    "NetSurf 3.11 has no Pedigree frontend or HOST definition. Its generic "
    "framebuffer frontend uses libnsfb, whose only SDL surface still targets "
    "SDL 1.2; the RAM surface has no display or input. The full source build "
    "also requires separately staged NetSurf component libraries, including "
    "libcss, libdom, libnsfb, libnsutils, and their build system."
)
