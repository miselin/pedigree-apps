UPSTREAM_VERSION = "4.6.0.20260123"

DISABLED_REASON = (
    "Pedigree's supported C library and final sysroot ABI is musl. GCC's "
    "stage-one --with-newlib flag only describes a compiler built before "
    "headers exist; the bootstrap does not build or install newlib, so a "
    "newlib target package would introduce a second incompatible libc."
)
