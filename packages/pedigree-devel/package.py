LEGACY_VERSION = "0.1"

DISABLED_REASON = (
    "This source-tree recipe emits legacy /include and /libraries paths and "
    "duplicates musl/CRT files from obsolete build locations. A replacement "
    "must package the maintained FHS sysroot export without moving libstdc++ "
    "out of the compiler prefix."
)
