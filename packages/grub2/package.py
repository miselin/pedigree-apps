UPSTREAM_VERSION = "2.12"

DISABLED_REASON = (
    "GRUB is a host-side boot-image tool, not a Pedigree target package. "
    "The legacy 2.00 recipe cross-builds it as x86_64-pedigree, while the "
    "current i386-pc image flow needs a separate native 2.12 build contract "
    "and a rebased platform patch."
)
