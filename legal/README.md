<!-- SPDX-License-Identifier: MPL-2.0 -->
# License notices

The repository's original work is licensed as described in its root README and LICENSE. Third-party components retain their own licenses and copyright notices, collected in [NOTICE.txt](NOTICE.txt) (written by `make notice`, `tools/make_notice.py`). Original NBTFoundry artwork is MPL-2.0.

| Component | Licence | Text |
| --- | --- | --- |
| This application (`src/`, `tests/`, `tools/`, build files) | MPL-2.0 | [LICENSE](../LICENSE) |
| NBT App SDK and its third-party parts | MPL-2.0; MIT, public domain | [MPL-2.0](../LICENSES/MPL-2.0.txt); NOTICE.txt |
| picolibc (the NBT toolchain's C library, linked into a module or a guest) | BSD-style | NOTICE.txt |
| compiler-rt, libc++, libc++abi, libunwind (linked in) | Apache-2.0 WITH LLVM-exception | no attribution owed in binaries |

The notices are a snapshot of the current dependencies. Update them when changing a bundled dependency, the SDK commit or the toolchain.

See [DISCLAIMER.md](../DISCLAIMER.md) for head-unit risks and warranty and liability terms.
