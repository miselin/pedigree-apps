UPSTREAM_VERSION = "2.46.1"

DISABLED_REASON = (
    "Binutils is supplied by the bootstrapped cross-toolchain. The legacy "
    "Pedigree target patches stop at 2.32; a self-hosted 2.46.1 package needs "
    "those BFD, GAS, and linker definitions rebased and validated independently "
    "from bootstrap."
)
