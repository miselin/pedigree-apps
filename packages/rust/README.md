# Rust 1.85.1 experimental bootstrap

This package supplies Rust, Cargo, rustdoc, the linker, and the standard library
for amd64 Pedigree through its Linux syscall ABI.

Use `pedigree-rustc example.rs -o example` or `pedigree-cargo build` to select
the installed sysroot and the executable layout required by Pedigree. The
upstream `rustc`, `rustdoc`, and `cargo` commands are also installed.

Compiler and Cargo startup have run on Pedigree. Native compilation, Cargo
dependency builds, and rustdoc remain experimental. This package does not
establish native compile/test/run qualification.

The upstream Rust 1.85.1 musl distribution is the compiler bootstrap. Its static
target libc is musl 1.2.3. The shared compiler uses Pedigree's system libc and a
bundled libgcc 14.2.0 runtime. Cargo's system trust store is supplied by the
`ca-certificates` package.

`bootstrap-provenance.json` records the component URLs, SHA-256 checksums, and
normalization tools. Rust and LLVM notices are in this directory; Cargo's
notices are in `/usr/share/doc/cargo`. Additional musl and GCC runtime notices
are under `licenses`.
