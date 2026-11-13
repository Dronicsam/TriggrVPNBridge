"""Host tests for package integrity, shell arguments and binary validation.
These do not emulate iOS or prove that private VPN APIs work on a device.
"""
import hashlib
import io
import plistlib
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_binary import validate_binary, verify_signature
from package import create_deb


def read_deb(path):
    raw = path.read_bytes()
    assert raw[:8] == b"!<arch>\n"
    result, pos = {}, 8
    while pos < len(raw):
        header = raw[pos:pos + 60]
        assert len(header) == 60 and header[58:] == b"`\n"
        size = int(header[48:58])
        result[header[:16].decode().strip().rstrip("/")] = raw[pos + 60:pos + 60 + size]
        pos += 60 + size + size % 2
    return result


class PackageTests(unittest.TestCase):
    def test_debian_archive_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            # A non-executable payload used ONLY to test the archive assembler.
            fake = directory / "fixture.dylib"
            fake.write_bytes(b"archive-test-only")
            output = create_deb(fake, directory / "one", 1234567890)
            self.assertNotIn("~", output.name)
            again = create_deb(fake, directory / "two", 1234567890)
            self.assertEqual(output.read_bytes(), again.read_bytes())
            members = read_deb(output)
            self.assertEqual(list(members), ["debian-binary", "control.tar.gz", "data.tar.gz"])
            self.assertEqual(members["debian-binary"], b"2.0\n")
            with tarfile.open(fileobj=io.BytesIO(members["data.tar.gz"]), mode="r:gz") as data:
                entries = {x.name.removeprefix("./"): x for x in data.getmembers()}
                for entry in entries.values():
                    self.assertEqual((entry.uid, entry.gid), (0, 0))
                    self.assertTrue(entry.name.startswith("./var"))
                    self.assertEqual(entry.mtime, 1234567890)
                self.assertEqual(entries["var/jb/usr/bin/triggr-vpn"].mode, 0o755)
                self.assertEqual(entries["var/jb/usr/libexec/triggr-vpn-action"].mode, 0o755)
                with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]), mode="r:gz") as control:
                    text = control.extractfile("./control").read().decode()
                    self.assertIn("Architecture: iphoneos-arm64", text)
                    self.assertIn("notifyutil", text)
                    self.assertNotIn("@VERSION@", text)
                    self.assertEqual(control.getmember("./postinst").mode, 0o755)
                    for line in control.extractfile("./md5sums").read().decode().splitlines():
                        digest, filename = line.split("  ", 1)
                        content = data.extractfile("./" + filename).read()
                        self.assertEqual(hashlib.md5(content).hexdigest(), digest)
            if shutil.which("dpkg-deb"):
                info = subprocess.run(["dpkg-deb", "--field", str(output), "Package"],
                                      check=True, capture_output=True, text=True)
                self.assertEqual(info.stdout.strip(), "local.triggrvpnbridge")

    def test_packaging_cli_rejects_invalid_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "bad.dylib"
            fake.write_bytes(b"not-mach-o")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/package.py"),
                                     "--binary", str(fake), "--output", str(Path(tmp) / "dist")],
                                    capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(list(Path(tmp).rglob("*.deb")))


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.mock = self.directory / "notifyutil"
        self.mock.write_text('#!/bin/sh\nprintf "<%s>\\n" "$@"\n')
        self.mock.chmod(0o755)
        source = (ROOT / "packaging/layout/var/jb/usr/bin/triggr-vpn").read_text()
        self.wrapper = self.directory / "triggr-vpn"
        self.wrapper.write_text(source.replace("/var/jb/usr/bin/notifyutil", str(self.mock)))

    def tearDown(self):
        self.temporary.cleanup()

    def run_wrapper(self, *arguments):
        return subprocess.run(["sh", str(self.wrapper), *arguments], capture_output=True, text=True)

    def test_valid_actions_post_exactly_one_notification(self):
        for action in ("toggle", "on", "off"):
            result = self.run_wrapper(action)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, f"<-p>\n<local.triggrvpnbridge.{action}>\n")

    def test_status_reads_instead_of_posting(self):
        self.assertEqual(self.run_wrapper("status").stdout,
                         "<-g>\n<local.triggrvpnbridge.status>\n")

    def test_rejects_extra_arguments_and_shell_payloads(self):
        for arguments in ((), ("toggle", "off"), ("$(touch nope)",), ("toggle; echo nope",)):
            result = self.run_wrapper(*arguments)
            self.assertEqual(result.returncode, 64)
            self.assertEqual(result.stdout, "")

    def test_dependency_failure_is_explicit(self):
        self.mock.unlink()
        result = self.run_wrapper("on")
        self.assertEqual(result.returncode, 69)
        self.assertIn("notifyutil is missing", result.stderr)

    def test_extension_matches_manifest_items(self):
        layout = ROOT / "packaging/layout"
        manifest = plistlib.loads((layout / "var/jb/Library/Triggr/Extensions/vpnbridge.plist").read_bytes())
        program = layout / manifest["Program"].lstrip("/")
        action_program = self.directory / "action"
        action_program.write_text(program.read_text().replace("/var/jb/usr/bin/triggr-vpn", str(self.mock)))
        items = layout / manifest["ItemsDirectory"].lstrip("/")
        expected = {"Toggle VPN": "toggle", "Turn VPN On": "on", "Turn VPN Off": "off"}
        self.assertEqual({p.stem for p in items.glob("*.action")}, set(expected))
        for title, action in expected.items():
            result = subprocess.run(["sh", str(action_program), title], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, f"<{action}>\n")
        result = subprocess.run(["sh", str(action_program), "Turn VPN On; echo nope"], capture_output=True)
        self.assertEqual(result.returncode, 64)

    def test_filter_is_springboard_only(self):
        path = ROOT / "packaging/layout/var/jb/Library/MobileSubstrate/DynamicLibraries/TriggrVPNBridge.plist"
        self.assertEqual(plistlib.loads(path.read_bytes())["Filter"],
                         {"Bundles": ["com.apple.springboard"]})


class SignatureTests(unittest.TestCase):
    def test_signed_page_tampering_is_detected(self):
        # Synthetic CodeDirectory fixture; not an executable or a distributable binary.
        code = bytes(4096)
        ident = b"test\0"
        hash_offset = 44 + len(ident)
        cd = struct.pack(">9I4BI", 0xFADE0C02, hash_offset + 32, 0x20001, 2,
                         hash_offset, 44, 0, 1, len(code), 32, 2, 0, 12, 0)
        cd += ident + hashlib.sha256(code).digest()
        signature = struct.pack(">5I", 0xFADE0CC0, 20 + len(cd), 1, 0, 20) + cd
        raw = code + signature
        verify_signature(raw, len(code), len(signature))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            verify_signature(b"!" + raw[1:], len(code), len(signature))


if __name__ == "__main__":
    unittest.main()
