LEGACY_VERSION = "0.1"

DISABLED_REASON = (
    "The main boot-artifacts target now builds src/modules/initrd.tar and a "
    "deterministic initrd.manifest, but it does not install or version that "
    "artifact. The package must consume an explicit module/initrd export "
    "instead of copying a mutable build directory."
)
