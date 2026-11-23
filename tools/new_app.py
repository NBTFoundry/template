#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Names a repository made from NBTFoundry/template after its application.

    tools/new_app.py <id> "<Title>" [--repo nf-<id>]

<id> is the application's id for NBT Manager (lower-case letters, digits and
hyphens; it never changes afterwards), <Title> its name as people read it.
Every "myapp", "My App" and "MYAPP" becomes the id and the title, the test
file is renamed, the repository's name replaces "template", the README loses
its "Start" section and this script removes itself. Run it once, in a clean
checkout, then `make notice` and `make -j"$(nproc)" host test`.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# Never rewritten: licence texts, artwork, generated files.
SKIP = ("LICENSE", "LICENSES/", "docs/assets/", "legal/NOTICE.txt", "tools/new_app.py")
SECTION = re.compile(r"<!-- template:start -->.*?<!-- template:end -->\n\n?", re.S)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("id", help="the application's id: [a-z][a-z0-9-]*, at most 24 characters")
    parser.add_argument("title", help='its name, as in "<Title> for NBT Manager"')
    parser.add_argument("--repo", help="the repository's name (default nf-<id>)")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,23}", args.id) or args.id == "myapp":
        sys.exit("the id is lower-case letters, digits and hyphens, starts with a letter, and is not myapp")
    if not args.title.strip() or "\n" in args.title:
        sys.exit("the title is one line of text")
    ident = args.id.replace("-", "_")  # where a hyphen cannot be: file and variable names
    repo = args.repo or f"nf-{args.id}"

    names = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard"],
                           check=True, capture_output=True, text=True).stdout.splitlines()
    for name in names:
        path = ROOT / name
        if name.startswith(SKIP) or not path.is_file():
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        new = text.replace("NBTFoundry/template", f"NBTFoundry/{repo}")
        new = new.replace("NBTFoundry template", f"NBTFoundry {repo}")
        new = new.replace("MYAPP", ident.upper()).replace("My App", args.title)
        new = new.replace("test_myapp", f"test_{ident}").replace("myapp", args.id)
        if name == "README.md":
            new = SECTION.sub("", new)
        if new != text:
            path.write_text(new)
    (ROOT / "tests/test_myapp.py").rename(ROOT / f"tests/test_{ident}.py")
    (ROOT / "legal/NOTICE.txt").unlink(missing_ok=True)
    Path(__file__).unlink()
    print(f'{repo}: application {args.id} ("{args.title}"). Next: make notice, make -j"$(nproc)" host test.')


if __name__ == "__main__":
    main()
