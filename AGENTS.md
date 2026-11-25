<!-- SPDX-License-Identifier: MPL-2.0 -->
# For coding agents

An application for NBT Manager on the NBT App SDK. Check out, next to this
repository:

- [NBTFoundry/sdk](https://github.com/NBTFoundry/sdk) as `../sdk`, at the
  commit in `release/sdk.ref`; `make -C ../sdk toolchain` once for the head
  unit's builds.
- [NBTFoundry/manager](https://github.com/NBTFoundry/manager) as
  `../manager`, for packaging and its documentation.

## Where to look

- The SDK's API: `../sdk/docs/api.md`; the three forms (module, guest,
  native) and the toolchain: `../sdk/docs/native-apps.md`.
- What NBT Manager gives an application (capabilities, limits, permissions):
  `../manager/docs/app-bridge.md`.
- The SDK's skills, `../sdk/.claude/skills/<name>/SKILL.md`. Written for ports,
  they hold for new applications too; read the one for the task first:

| Task | Skill |
| --- | --- |
| The Makefile and builds | `port-build` |
| The form on the head unit | `port-module` |
| Controls: iDrive controller, gamepads, keyboard | `port-controls` |
| Tests without a car | `port-tests` |
| The package (`release/package.args`) | `port-package` |
| Licences and `legal/NOTICE.txt` | `port-licence` |
| Speed on the head unit | `port-perf` |
| A build or run problem on the head unit | `port-qnx-fixes` |
| CI and signed releases | `port-release` |
| A test in the car | `port-car-test` |
| Something the SDK or NBT Manager lacks | `port-sdk-gap` |

## Rules

- Before a commit: `make -j"$(nproc)" host test test-asan check-static-init`;
  `make notice` when a dependency, the SDK or the toolchain changes.
- C++11 without exceptions or RTTI; nothing runs before `main` (no static
  constructors).
- Third-party code as git submodules in `third_party/`, unmodified.
- Never commit a private key; only `release/developer-public.pem`.
