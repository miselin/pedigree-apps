UPSTREAM_VERSION = "11.1.0"

DISABLED_REASON = (
    "QEMU is a native host emulator used to run Pedigree, not software for "
    "the Pedigree root filesystem. The old entry has no source URL, target, "
    "or install contract; keep QEMU in the local builder/tooling layer."
)
