UPSTREAM_VERSION = "0.74-3"

DISABLED_REASON = (
    "Classic DOSBox 0.74-3 still requires SDL 1.2, which is not present in "
    "the FHS package catalog. The old recipe hard-codes "
    "/applications/sdl-config and cannot configure or link in the current "
    "sysroot."
)
