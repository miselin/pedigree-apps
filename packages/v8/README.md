# V8 on Pedigree

V8 13.6.233.17 supplies an embeddable JavaScript engine for amd64 Pedigree.
The package installs C++ headers under `/usr/include/v8`, a static library
at `/usr/lib/libv8.a`, and `v8.pc` for pkg-config. C++20 is required.

Use the pkg-config flags when compiling and linking an embedding application:

```sh
g++ $(pkg-config --cflags v8) example.cc -o example $(pkg-config --static --libs v8)
```

These flags also select the matching Promise embedder-field layout.

`v8-qualify jitless`, `v8-qualify jit`, and `v8-qualify jit-default` exercise the embedding API. The
example source is installed in `/usr/share/doc/v8/probe.cc`.

The initial configuration includes Sparkplug and TurboFan JIT compilation.
ICU/Intl, Maglev, pointer compression, and the V8 sandbox are disabled.
WebAssembly and inspector support are built but their runtime behavior is
not yet qualified.
The normal 512 MiB code reservation requires Pedigree's large sparse mapping
fixes in `fff825465` or later. The qualification example also covers a smaller
64 MiB code reservation, with a 64 MiB heap and a 512 KiB JavaScript stack budget.

This port uses the V8 sources and build dependencies from the pinned Node
24.20.0 source release. It builds only V8 library targets. Node.js and npm
are separate follow-up ports.

The example covers bounded JavaScript embedding and baseline JIT workloads;
large heaps and sustained concurrent JIT/GC need broader qualification.
Build provenance and third-party license notices are included alongside this file.
