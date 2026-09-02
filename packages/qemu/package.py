UPSTREAM_VERSION = "11.1.1"

DISABLED_REASON = (
    "QEMU 11.1.1 is a native host emulator used to run Pedigree, not "
    "software for the Pedigree root filesystem. It belongs in the local "
    "host tooling layer and has no target package or runtime contract."
)
