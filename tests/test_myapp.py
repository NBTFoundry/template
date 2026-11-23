# SPDX-License-Identifier: MPL-2.0
"""The desktop build as NBT Manager starts it: the health check without a
window, a user launch under Xvfb with the iDrive controller's socket; the
signed package's declaration; the notices being current."""

import os
from pathlib import Path
import re
import select
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = Path(os.environ.get("NBT_MYAPP_APP", ROOT / "build/nbt-myapp-host"))
MGR_DIR = Path(os.environ.get("NBT_MGR_DIR", ROOT.parent / "manager"))
SDK_DIR = Path(os.environ.get("NBT_SDK_DIR", ROOT.parent / "sdk"))
FORM = os.environ.get("NBT_APP_FORM", "module")  # the Makefile's FORM

BACK = 1 << 2  # the SDK's nbt/controller_wire.h


def controller_state(sequence, keys=0, rotation=0):
    return struct.pack("<BBBBIIi", 0x43, 1, 1, 0, sequence, keys, rotation)


def xvfb():
    r, w = os.pipe()
    proc = subprocess.Popen(
        ["Xvfb", "-displayfd", str(w), "-screen", "0", "1280x480x24", "-nolisten", "tcp"],
        pass_fds=(w,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(w)
    number = b""
    while not number.endswith(b"\n"):
        ready, _, _ = select.select([r], [], [], 10)
        chunk = os.read(r, 1) if ready else b""
        if not chunk:
            break
        number += chunk
    os.close(r)
    return proc, ":" + number.decode().strip()


class App:
    """The application, its log (standard error) read by line."""

    def __init__(self, env, args=(), pass_fds=()):
        full = {k: v for k, v in os.environ.items() if not k.startswith("NBT_")}
        full.update(env)
        self.proc = subprocess.Popen([str(APP), *args], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE, env=full, pass_fds=pass_fds)
        self.lines, self.seen, self.buf = [], [], b""

    def wait(self, pattern, timeout=20.0):
        regex, deadline = re.compile(pattern), time.monotonic() + timeout
        while True:
            while b"\n" in self.buf:
                raw, self.buf = self.buf.split(b"\n", 1)
                line = raw.decode(errors="replace")
                self.lines.append(line)
                self.seen.append(line)
            for i, line in enumerate(self.lines):
                if regex.search(line):
                    del self.lines[: i + 1]
                    return line
            fd = self.proc.stderr.fileno()
            left = deadline - time.monotonic()
            ready, _, _ = select.select([fd], [], [], max(0.0, left)) if left > 0 else ([], [], [])
            chunk = os.read(fd, 4096) if ready else b""
            if not chunk:
                raise AssertionError(f"no line matching {pattern!r}; saw {self.seen[-30:]!r}")
            self.buf += chunk

    def stop(self, sig=signal.SIGTERM):
        """Sends `sig` (None: only waits for the end) and returns the status."""
        if sig is not None and self.proc.poll() is None:
            self.proc.send_signal(sig)
        _, err = self.proc.communicate(timeout=20)
        self.buf += err
        return self.proc.returncode


@unittest.skipUnless(os.access(APP, os.X_OK), f"{APP} not built")
class CheckLaunchTest(unittest.TestCase):
    def test_reports_ready_without_a_window(self):
        """As NBT Manager runs it after an install or an update: no display,
        ready on --ready-fd, heartbeats, then SIGTERM ends it with status 0."""
        with tempfile.TemporaryDirectory() as data:
            lease_fd = os.open(Path(data) / "lease", os.O_CREAT | os.O_RDWR, 0o600)
            rfd, wfd = os.pipe()
            env = {"NBT_LAUNCH": "check", "NBT_DATA_DIR": data}
            app = App(env, ["--ready-fd", str(wfd), "--lease-fd", str(lease_fd)], (wfd, lease_fd))
            os.close(wfd)
            try:
                app.wait(r"ready, 1280x480")
                for _ in range(2):  # ready, then a heartbeat
                    readable, _, _ = select.select([rfd], [], [], 5.0)
                    self.assertEqual(os.read(rfd, 1) if readable else b"", b"R")
                self.assertEqual(app.stop(), 0, app.seen[-20:])
            finally:
                if app.proc.poll() is None:
                    app.proc.kill()
                os.close(rfd)
                os.close(lease_fd)


@unittest.skipUnless(os.access(APP, os.X_OK), f"{APP} not built")
@unittest.skipUnless(shutil.which("Xvfb"), "Xvfb not installed")
class UserLaunchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nbt-myapp-"))
        self.x, self.display = xvfb()
        self.controller_app, self.controller = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)

    def tearDown(self):
        self.controller_app.close()
        self.controller.close()
        self.x.terminate()
        self.x.wait(timeout=5)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def start(self, **settings):
        env = {
            "NBT_LAUNCH": "user", "DISPLAY": self.display, "LIBGL_ALWAYS_SOFTWARE": "1",
            "NBT_NO_AUDIO": "1", "NBT_DATA_DIR": str(self.tmp),
            "NBT_BRIDGE_CAPS": "show,controller",
            "NBT_CONTROLLER_FD": str(self.controller_app.fileno()),
        }
        env.update({"NBT_SETTING_" + k.upper(): v for k, v in settings.items()})
        app = App(env, pass_fds=(self.controller_app.fileno(),))
        self.addCleanup(lambda: app.proc.poll() is None and app.proc.kill())
        app.wait(r"ready, 1280x480, caps show,controller")
        return app

    def test_it_runs_and_stops_when_asked(self):
        app = self.start(debug_log="on")
        time.sleep(0.5)
        self.assertIsNone(app.proc.poll())
        self.assertEqual(app.stop(), 0, app.seen[-20:])

    def test_a_long_back_hold_quits(self):
        app = self.start()
        self.controller.send(controller_state(1))  # keys count once all were seen up
        self.controller.send(controller_state(2, BACK))
        app.wait(r"BACK held: closing", timeout=3)
        self.assertEqual(app.stop(None), 0, app.seen[-20:])


class PackageTest(unittest.TestCase):
    def test_the_package_declares_its_bridge_and_settings(self):
        """The Makefile's FORM, signed with a throw-away key: with the runner
        (module, guest) bridge 1.7 and `runner`; native, neither."""
        verify = MGR_DIR / "build" / "nbt-verify"
        if not (MGR_DIR / "tools/package.py").exists() or not verify.exists():
            self.skipTest("the manager's tools/package.py or build/nbt-verify is missing")
        if not shutil.which("openssl"):
            self.skipTest("openssl is missing")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            key, public = tmp / "app.key", tmp / "app.pub"
            subprocess.run(["openssl", "genrsa", "-out", key, "3072"], check=True, capture_output=True)
            subprocess.run(["openssl", "rsa", "-in", key, "-pubout", "-out", public], check=True,
                           capture_output=True)
            # A stand-in for the payload: an ARM ELF header; with the runner it
            # carries the SDK's NBT ABI note, as the packer wants with `runner`.
            elf = bytearray(52)
            elf[:7] = b"\x7fELF\x01\x01\x01"
            if FORM == "native":
                elf[16:20] = b"\x02\x00\x28\x00"
                binary, payload = tmp / "stand-in", bytes(elf)
            else:
                note = struct.pack("<III", 4, 12, 1) + b"NBT\0" + struct.pack("<III", 1, 1, 1)
                struct.pack_into("<HHI", elf, 16, 3, 40, 1)
                struct.pack_into("<I", elf, 28, 52)
                struct.pack_into("<HHH", elf, 40, 52, 32, 1)
                phdr = struct.pack("<IIIIIIII", 4, 84, 0, 0, len(note), len(note), 4, 4)
                binary, payload = tmp / "stand-in.so", bytes(elf) + phdr + note
            binary.write_bytes(payload)
            subprocess.run(["make", "-s", "-C", str(ROOT), "package", f"FORM={FORM}", f"BUILD_DIR={tmp}",
                            f"PACKAGE_INPUT={binary}", f"APP_KEY={key}", f"NBT_MGR_DIR={MGR_DIR}",
                            f"NBT_SDK_DIR={SDK_DIR}", "APP_VERSION=0.1.0", "APP_SEQ=1000"],
                           check=True, capture_output=True)
            out = subprocess.run([str(verify), str(tmp / "myapp-0.1.0.nbt"), str(public), "myapp",
                                  "nbt_6.5_armv7"], check=True, capture_output=True, text=True).stdout
            self.assertIn("app=myapp\n", out)
            if FORM == "native":
                self.assertIn("bridge=1.5\n", out)
                self.assertIn("bridge-uses=show,controller\n", out)
            else:
                self.assertIn("bridge=1.7\n", out)
                self.assertIn("bridge-uses=show,controller,runner\n", out)
            self.assertIn("bridge-optional=status,live-settings\n", out)


class NoticeTest(unittest.TestCase):
    def test_the_notices_are_current(self):
        if not (SDK_DIR / "tools/third_party_notices.py").exists():
            self.skipTest("no SDK checkout for its notices")
        check = subprocess.run([sys.executable, str(ROOT / "tools/make_notice.py"), "--check"],
                               env=dict(os.environ, NBT_SDK_DIR=str(SDK_DIR)),
                               capture_output=True, text=True)
        if check.returncode and "no picolibc notices" in check.stderr:
            self.skipTest("no NBT toolchain for its notices")
        self.assertEqual(check.returncode, 0, check.stderr)


if __name__ == "__main__":
    unittest.main()
