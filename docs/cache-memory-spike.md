# Cache memory growth during compiler startup

Reading one byte from each of 256 distinct 4 KiB files consumed **515.8 MiB** on
Pedigree `192bf30cb55392ce6b1026d427b30b7545e1b524`. The same probe consumes about
**5.1 MiB** after `0139dd022418a0fd72baa812f80b4724e44e09b8`
(`cache: bound per-inode lookup filter memory`). Repeating the reads adds almost
no memory. This establishes first-touch cache metadata growth as the repaired
problem. Native Go now completes the dependency walk that previously exhausted
kernel memory. The repaired-kernel suite subsequently timed out during the
cold native build at its 900-second overall limit, without an OOM; native
compile/test/run remains unqualified. That run is retained at
`.build/memory-spike/go-native-1cpu/`.

Each ext2 inode has a file cache. Its Bloom filter previously used 15,204,352
bits and 11 hashes. Inserting the first page at offset zero allocated a
1,660,888-byte bitmap, which Pedigree's allocator rounds to a 2 MiB size class.
That cost applied even when the caller read only one byte.

The repair changes only the cache's filter configuration to 4,096 bits and four
hashes. The first page now requests 472 bitmap bytes. The maximum dynamic bitmap
allocation is 511 bytes, plus an eight-byte static word; allocator and object
overhead are additional. A saturated filter can produce more false positives,
but every positive result still consults the authoritative page tree. No cache
ownership or writeback behavior changed.

The public syscall probe opens, verifies one byte, and closes each file, then
repeats the full pass. It measures free memory through `sysinfo` and requires
total loss below 64 MiB. All runs used 1 GiB RAM, a 2 GiB ext2 disk, QEMU's `max`
CPU, serial output, and independent image copies with `-snapshot`. Fixed images
were rebuilt from the exact source subsequently committed as `0139dd022`.

| Kernel / CPUs | First pass loss, KiB | Repeat loss, KiB | Total loss, KiB | Result |
| --- | ---: | ---: | ---: | --- |
| Baseline / 1 | 528,228 | 0 | 528,228 | Failed 64 MiB budget |
| Fixed / 1 | 5,216 | 4 | 5,220 | Passed |
| Fixed / 4 | 5,220 | 8 | 5,228 | Passed |

The fixed runs verified the probe's pass line, shell exit status, and final
`LANGUAGE-PORTS: END PASS` marker. `PEDIGREE_CRIPPLE_HDD=TRUE` remained enabled;
these results do not establish persistent disk writeback.

Reproduce from the pedigree-apps root, with the sibling Pedigree checkout and
its cross compiler available:

```sh
mkdir -p .build/memory-spike/probe
../pedigree/pedigree-compiler-15.3.0-r2/bin/x86_64-pedigree-gcc \
  -static -O2 -Wall -Wextra language-ports/cache-memory/probe.c \
  -o .build/memory-spike/probe/cache-spike
python3 - <<'PY'
from pathlib import Path
directory = Path('.build/memory-spike/probe/inputs')
directory.mkdir(parents=True, exist_ok=True)
for i in range(256):
    (directory / f'{i:04d}.dat').write_bytes(bytes([i % 255 + 1]) * 4096)
PY
cmake --build ../pedigree/build --target livecd hddimage -j2
python3 scripts/qualify-language-ports.py \
  --iso ../pedigree/build/pedigree.iso --disk ../pedigree/build/hdd.img \
  --suite language-ports/cache-memory/suite.json \
  --memory 1024 --cpus 1 --timeout 300 \
  --output-dir .build/memory-spike/recheck-1cpu
```

Use `--cpus 4` and a fresh output directory for SMP verification. The harness
copies both input images and records payload hashes and the QEMU command.
Build images only while no guest is using the build's backing artifacts.

The retained local evidence is under `.build/memory-spike/`: `baseline-1cpu`,
`fixed-1cpu`, and `fixed-4cpu` each contain `result.json`, `metadata.json`, and
`serial.log`. These generated artifacts are not versioned. Their saved
`boot.iso` files preserve the tested kernel versions. Allocation measurements
and the initial candidate patch are in `cache/`.

The new host allocation regression failed with the original constructor, then
**32 focused Cache, BloomFilter, and ExtensibleBitmap tests passed** with the
repair. Coverage includes independent small caches, saturated-filter lookups,
an actual false-positive miss, eviction, and reinsertion. Logs are
`host-cache-baseline.log` and `host-cache-fixed.log`; exact focused link commands
are retained in `cache-tests-*-link.json`. The focused objects were rebuilt and
linked against the current libraries in the Linux host build environment. In
that environment the retained binaries can be rerun directly:

```sh
.build/memory-spike/cache-tests-baseline \
  --gtest_filter=CacheMemory.FirstPageMetadataStaysSmallAcrossIndependentCaches
.build/memory-spike/cache-tests-fixed
```

The full kernel host suite was not completed: the macOS build encountered
existing missing-`override` errors in `RamFs.h`, and the Linux build encountered
an existing packed-field reference error in `test-Ext2FillCache.cc:341`.
`host-baseline-build.log` and `linux-host-baseline-build.log` retain those
failures. The separate pedigree-apps regression suite passed 288 tests
(`apps-tests.log`).

A separate, unprofiled performance issue remains: `Cache::timer` restarts its
ordered scan after each dirty page and can checksum earlier clean pages
repeatedly within one epoch. Failed writebacks under `CRIPPLE_HDD` perpetuate
the work. Rust image allocation order placed dirty pages after the large
compiler driver in slower runs, which provides a plausible explanation for the
timing difference. The driver itself remained below 2 GiB with nearly identical
block layouts. This follow-up needs its own timing evidence and regression;
it is excluded from the memory repair.
