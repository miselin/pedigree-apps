UPSTREAM_VERSION = "0.82.2"

DISABLED_REASON = (
    "DOSBox Staging 0.82.2 requires a functional SDL2 video, input, and "
    "audio frontend; the current Pedigree SDL2 compatibility profile is "
    "intentionally offscreen-only. Its mandatory static build dependencies "
    "iir, opusfile (plus opus and ogg), and SpeexDSP are also not yet in the "
    "FHS package catalog. zlib and libpng are already available."
)
