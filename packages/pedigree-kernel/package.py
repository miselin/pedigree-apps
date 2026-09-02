LEGACY_VERSION = "0.1"

DISABLED_REASON = (
    "The main boot-artifacts target builds kernel-mini64 and its diagnostic "
    "kernel, but is explicitly an aggregate build target rather than an "
    "installer or staging directory. A versioned /boot export and an agreed "
    "debug-file destination are required before this can be a PUP package."
)
