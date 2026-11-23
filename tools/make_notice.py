#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Writes legal/NOTICE.txt: the notices the application's package carries.

Ours (MPL-2.0), the third-party notices of the NBT App SDK it links
(NBT_SDK_DIR, default ../sdk), and picolibc, which the NBT toolchain's
runtime links statically (NBT_TOOLCHAIN, default the SDK's installed
release). Add to `parts` the licence and the notices of what the application
bundles (an upstream project, a library), read from the submodule's own
files, never retyped. Run again (`make notice`) when a dependency, the SDK or
the toolchain changes; with --check (`make test`), fails when the file is out
of date.
"""
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SDK = Path(os.environ.get("NBT_SDK_DIR", ROOT.parent / "sdk"))
RULE = "\n" + "=" * 72 + "\n\n"

HEADER = """NBTFoundry

NBTFoundry template
Copyright (c) 2026 Fabien Poussin
Original software: MPL-2.0. You may redistribute and modify it under that license.
This software comes WITHOUT ANY WARRANTY, to the extent permitted by law.
Original NBTFoundry artwork: MPL-2.0. Trademark rights are separate.
Source: https://github.com/NBTFoundry/template
When redistributing binaries, include applicable notices and provide the source required by the component licenses.
"""


def toolchain() -> Path:
    if os.environ.get("NBT_TOOLCHAIN"):
        return Path(os.environ["NBT_TOOLCHAIN"])
    version = re.search(r"^NBT_TOOLCHAIN_VERSION := (\S+)", (SDK / "module/flags.mk").read_text(), re.M)
    return SDK / "toolchain" / f"nbt-toolchain-{version.group(1)}"


def main():
    runtime = toolchain() / "share/licenses/picolibc"
    if not runtime.is_dir():
        sys.exit(f"no picolibc notices in {runtime}: run make toolchain in the SDK or set NBT_TOOLCHAIN")
    sdk_notices = subprocess.run([sys.executable, str(SDK / "tools/third_party_notices.py")],
                                 check=True, capture_output=True, text=True).stdout
    parts = [
        HEADER,
        "Head-unit risk and disclaimer\n\n" + (ROOT / "DISCLAIMER.md").read_text().split("\n", 2)[2],
        "MPL-2.0: this application and the NBT App SDK (https://github.com/NBTFoundry/sdk)\n\n"
        + (ROOT / "LICENSES/MPL-2.0.txt").read_text(),
        sdk_notices,
        "picolibc, the C library of the NBT toolchain's runtime, linked statically "
        "(https://github.com/picolibc/picolibc)\n\n"
        + (runtime / "COPYING.picolibc").read_text() + RULE.lstrip("\n")
        + "picolibc's newlib-derived parts\n\n" + (runtime / "COPYING.NEWLIB").read_text(),
    ]
    text = "\n\n" + RULE.join(p.rstrip("\n") + "\n" for p in parts)
    out = ROOT / "legal/NOTICE.txt"
    if "--check" in sys.argv:
        if not out.exists() or out.read_text() != text:
            sys.exit("legal/NOTICE.txt is out of date: run make notice")
        return
    out.parent.mkdir(exist_ok=True)
    out.write_text(text)
    print(f"legal/NOTICE.txt: {len(parts)} sections")


if __name__ == "__main__":
    main()
