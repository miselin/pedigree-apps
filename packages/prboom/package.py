UPSTREAM_VERSION = "2.6.66"

DISABLED_REASON = (
    "PrBoom+ 2.6.66 is the final release of the archived upstream. A "
    "playable port requires a functional Pedigree SDL2 video and input "
    "frontend; the current compatibility profile is offscreen-only. Its "
    "cross build also requires a native first stage to export the WAD "
    "generator targets before compiling the Pedigree executable."
)
