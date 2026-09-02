UPSTREAM_VERSION = "22.1.8"

DISABLED_REASON = (
    "LLVM 22.1.8 is the current stable release, but Pedigree uses it only as "
    "a host analysis toolchain. Pedigree's maintained target compiler "
    "family is GCC, and LLVM has no Pedigree triple/driver, runtime, "
    "resource-directory, or target install contract."
)
