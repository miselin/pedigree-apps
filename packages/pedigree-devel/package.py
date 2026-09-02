LEGACY_VERSION = "0.1"

DISABLED_REASON = (
    "The main build has no CMake install target or versioned SDK/sysroot "
    "export. Its bootstrap stages musl into the target sysroot while libgcc "
    "and libstdc++ remain owned by the compiler prefix; copying build-tree "
    "headers, CRT objects, or libraries would violate that boundary."
)
