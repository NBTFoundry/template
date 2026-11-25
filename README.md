<!-- SPDX-License-Identifier: MPL-2.0 -->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.svg">
    <img src="docs/assets/logo-light.svg" alt="NBTFoundry" height="44">
  </picture>
</p>

<h1 align="center">My App for NBT Manager</h1>

> **Warning: installing or modifying this software can brick your head unit. Recovery may require professional service or replacement, at your expense. Provided AS IS; use at your own risk, subject to applicable law.** [Read the risk and liability disclaimer](DISCLAIMER.md).

An application for the iDrive screen on the [NBT App SDK](https://github.com/NBTFoundry/sdk),
installed and launched through [NBT Manager](https://github.com/NBTFoundry/manager).

**Supported head units:** BMW NBT Evo (iDrive 6).

Not affiliated with or endorsed by BMW AG. BMW, iDrive and NBT are trademarks
of BMW AG.

<!-- template:start -->
## Start

This repository is a template: the least an application needs, ready to
build. `src/main.cpp` opens the window, shows a name, keeps NBT Manager's
heartbeat and stops on a long BACK hold.

1. **Make your repository** from it, next to `sdk` and `manager`:
   ```sh
   gh repo create <owner>/nf-<id> --public --template NBTFoundry/template
   git clone git@github.com:<owner>/nf-<id>.git && cd nf-<id>
   ```
2. **Name it:** `tools/new_app.py <id> "<Title>"` replaces `myapp` and
   `My App` everywhere, removes this section and itself. The id is NBT
   Manager's name for the application and never changes.
3. **Build and run** it on the desktop: [Build](#build).
4. **Choose the form** it takes on the head unit: [The form](#the-form).
5. **Write the application** in `src/main.cpp`, where its comments say.
   The [examples](https://github.com/NBTFoundry/examples) show controls for
   the iDrive controller and gamepads, settings and a status line, and a
   screen made of LVGL widgets; the SDK's
   [API](https://github.com/NBTFoundry/sdk/blob/main/docs/api.md) has the rest.

To port an existing program (a game, an emulator, a tool) rather than write
one, follow the SDK's [porting guide](https://github.com/NBTFoundry/sdk/blob/main/docs/porting.md):
the program's licence decides the form. Before a first release: the
`release` environment and signing secret on GitHub, and a test in the car
(the guide's `port-release` and `port-car-test` steps).
<!-- template:end -->

## Build

Needs the NBT App SDK next to this repository (`../sdk`, or `NBT_SDK_DIR`),
gcc, Python 3, and the X11, EGL and GLESv2 development files; Xvfb for the
tests.

```sh
make -j"$(nproc)" host test test-asan check-static-init   # host binary and tests
./build/nbt-myapp-host                                    # on the desktop (X11); Escape closes it
```

The tests start the desktop build as NBT Manager does: a health check without
a window, then a launch under Xvfb. The package test needs NBT Manager's
checkout (`../manager`, or `NBT_MGR_DIR`) with `nbt-verify` built
(`make -C ../manager host`); it is skipped without.

Head unit, with the NBT toolchain (`make -C ../sdk toolchain` once):

```sh
make -j"$(nproc)" module                              # build/nbt-myapp.so
make vm-test                                          # in the SDK's VM
make APP_KEY=/path/to/apps-signing-key.pem package    # build/myapp-<version>.nbt
```

`release/package.args` describes the package: the id, the capabilities and
the settings. `release/sdk.ref` is the SDK commit CI and releases build
against. `make notice` writes `legal/NOTICE.txt`; `make test` fails when it
lags.

## Your own key

Without NBTFoundry's apps key, sign with a key of your own and add it to your
car once (an NBT Manager with developer keys):

```sh
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out ~/.nbt/myapp-key.pem  # keep it private
openssl pkey -in ~/.nbt/myapp-key.pem -pubout -out release/developer-public.pem
make APP_KEY=~/.nbt/myapp-key.pem package
```

- **On the car:** copy `release/developer-public.pem` to the phone; in the
  NBT Manager app, Car › Manage › Developer keys › Pick a key file, then
  confirm the same fingerprint on the car. Packages signed with that key then
  install from the phone.
- **Releases from CI:** the private key, base64, as `APPS_SIGNING_KEY` in the
  `release` environment, and `public-key: release/developer-public.pem` under
  `with:` in `.github/workflows/release.yml`.

## The form

An application reaches the head unit in one of three forms. `FORM` in the
`Makefile` names it; `vm-test` and `package` follow it.

| `FORM` | For | Builds | Package |
| --- | --- | --- | --- |
| `module` (the default) | code that is not GPL or LGPL: NBT Manager's `nbt-runner` loads it into its own process | `make module`, `build/nbt-myapp.so` | bridge 1.7, `runner` |
| `guest` | GPL or LGPL code, even one file: `nbt-runner` starts it as its child process | `make guest`, `build/nbt-myapp.guest` | bridge 1.7, `runner` |
| `native` | a program that needs the car's own libraries, other processes or sockets, without the runner: NBT Manager starts it itself | `make native native-check`, `build/nbt-myapp-native` | bridge 1.5, no `runner` |

For another form than `module`: set `FORM` in the `Makefile` and the last two
lines of `.github/workflows/release.yml`; for `native`, also move
`release/native.args`'s lines into `release/package.args`. `APP_LICENSE` in
the `Makefile` names the licence of every linked object: the link refuses GPL
or LGPL code in a module.

## Releases

`.github/workflows/ci.yml` runs the host tests, the same under ASan/UBSan and
the head-unit builds on every push and pull request. A `vX.Y.Z` tag runs
`.github/workflows/release.yml`: NBT Manager's application release workflow
builds the payload, signs it with the apps key after a maintainer approves
the run (the `release` environment, secret `APPS_SIGNING_KEY`) and publishes
`myapp-X.Y.Z.nbt`, sequence `X*1000000 + Y*1000 + Z`.

## License

Copyright (c) 2026 Fabien Poussin. Original code, tests, build scripts and
documentation are licensed under **MPL-2.0**; see [LICENSE](LICENSE).

Original NBTFoundry logos and artwork are MPL-2.0; copyright permission for
artwork does not grant trademark rights or imply endorsement by BMW AG.

See [legal/README.md](legal/README.md) for third-party license notices.
