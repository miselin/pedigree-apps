UPSTREAM_VERSION = "4.6.0.20260123"

DISABLED_REASON = (
    "Pedigree now uses musl as its C library and sysroot ABI. Newlib is no "
    "longer part of the supported toolchain, and the old entry never had a "
    "source, build, or install recipe."
)
