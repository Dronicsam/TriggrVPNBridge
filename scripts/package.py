#!/usr/bin/env python3
"""Create a deterministic .deb using Python's standard library on macOS/Linux."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import os
import re
import shutil
import tarfile
import tempfile
from pathlib import Path

from check_binary import validate_binary

ROOT = Path(__file__).resolve().parents[1]


def tar_gzip(directory: Path, epoch: int) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=epoch) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar:
            for path in sorted(directory.rglob("*")):
                if path.is_symlink():
                    raise ValueError(f"Unexpected symlink: {path}")
                name = "./" + path.relative_to(directory).as_posix()
                info = tar.gettarinfo(str(path), arcname=name)
                info.uid = info.gid = 0
                info.uname = info.gname = "root"
                info.mtime = epoch
                if path.is_file():
                    with path.open("rb") as stream:
                        tar.addfile(info, stream)
                else:
                    tar.addfile(info)
    return output.getvalue()


def ar_member(name: str, data: bytes, epoch: int) -> bytes:
    header = f"{name + '/':<16}{epoch:<12}{0:<6}{0:<6}{'100644':<8}{len(data):<10}`\n"
    if len(header.encode("ascii")) != 60:
        raise ValueError("Invalid ar member header")
    return header.encode("ascii") + data + (b"\n" if len(data) % 2 else b"")


def create_deb(binary: Path, destination: Path, epoch: int = 0) -> Path:
    """Assemble a package; callers distributing it must validate_binary first."""
    version = (ROOT / "VERSION").read_text().strip()
    if not re.fullmatch(r"[0-9][A-Za-z0-9.+~]*", version):
        raise ValueError("Invalid VERSION")
    if not 0 <= epoch < 10**11:
        raise ValueError("SOURCE_DATE_EPOCH out of range")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="triggr-vpn-package-") as temporary:
        stage = Path(temporary)
        payload, control_dir = stage / "data", stage / "control"
        shutil.copytree(ROOT / "packaging/layout", payload)
        control_dir.mkdir()
        dylib = payload / "var/jb/Library/MobileSubstrate/DynamicLibraries/TriggrVPNBridge.dylib"
        shutil.copyfile(binary, dylib)
        dylib.chmod(0o755)
        executables = {"triggr-vpn", "triggr-vpn-action"}
        for path in payload.rglob("*"):
            path.chmod(0o755 if path.is_dir() or path.name in executables or path == dylib else 0o644)
        control = (ROOT / "packaging/DEBIAN/control.in").read_text().replace("@VERSION@", version)
        size = sum(p.stat().st_size for p in payload.rglob("*") if p.is_file())
        (control_dir / "control").write_text(control + f"Installed-Size: {(size + 1023) // 1024}\n")
        for name in ("postinst", "postrm"):
            shutil.copyfile(ROOT / "packaging/DEBIAN" / name, control_dir / name)
            (control_dir / name).chmod(0o755)
        md5s = []
        for path in sorted(payload.rglob("*")):
            if path.is_file():
                digest = hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()
                md5s.append(f"{digest}  {path.relative_to(payload).as_posix()}\n")
        (control_dir / "md5sums").write_text("".join(md5s))
        for name in ("control", "md5sums"):
            (control_dir / name).chmod(0o644)
        archive = b"!<arch>\n"
        for name, data in (("debian-binary", b"2.0\n"),
                           ("control.tar.gz", tar_gzip(control_dir, epoch)),
                           ("data.tar.gz", tar_gzip(payload, epoch))):
            archive += ar_member(name, data, epoch)
        result = destination / f"local.triggrvpnbridge_{version}_iphoneos-arm64.deb"
        result.write_bytes(archive)
        digest = hashlib.sha256(archive).hexdigest()
        result.with_suffix(".deb.sha256").write_text(f"{digest}  {result.name}\n")
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    validate_binary(args.binary)
    print(create_deb(args.binary, args.output, int(os.environ.get("SOURCE_DATE_EPOCH", "0"))))
