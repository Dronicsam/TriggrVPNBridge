#!/usr/bin/env python3
"""Validate slices, platform, dependencies and code hashes before packaging."""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify_signature(data: bytes, offset: int, size: int) -> None:
    require(offset + size <= len(data), "Signature extends beyond slice")
    magic, length, count = struct.unpack_from(">III", data, offset)
    require(magic == 0xFADE0CC0 and length <= size, "Invalid signature superblob")
    require(12 + count * 8 <= length, "Invalid signature index")
    verified = False
    for i in range(count):
        _, relative = struct.unpack_from(">II", data, offset + 12 + i * 8)
        require(relative + 8 <= length, "Invalid signature entry")
        start = offset + relative
        cd_magic, cd_length = struct.unpack_from(">II", data, start)
        require(relative + cd_length <= length, "Signature entry exceeds superblob")
        if cd_magic != 0xFADE0C02:
            continue
        require(cd_length >= 44, "Truncated CodeDirectory")
        _, _, _, _, hash_offset, _, _, slots, limit = struct.unpack_from(">9I", data, start)
        hash_size, hash_type, _, page_exp = struct.unpack_from(">4B", data, start + 36)
        require(page_exp in range(12, 17), "Unexpected code-signing page size")
        require(limit <= offset, "CodeDirectory covers its own signature")
        page_size = 1 << page_exp
        require(slots == (limit + page_size - 1) // page_size, "Wrong signed page count")
        require(hash_offset + slots * hash_size <= cd_length, "Invalid code hash table")
        require(hash_type in (1, 2, 3), "Unsupported code hash type")
        require(hash_size == {1: 20, 2: 32, 3: 20}[hash_type], "Wrong code hash length")
        for slot in range(slots):
            page = data[slot * page_size:min((slot + 1) * page_size, limit)]
            digest = (hashlib.sha1(page).digest() if hash_type == 1
                      else hashlib.sha256(page).digest())[:hash_size]
            pos = start + hash_offset + slot * hash_size
            require(data[pos:pos + hash_size] == digest, "Code signature page hash mismatch")
        verified = True
    require(verified, "No supported CodeDirectory found")


def validate_binary(path: Path) -> None:
    raw = path.read_bytes()
    require(len(raw) >= 8 and raw[:4] == b"\xca\xfe\xba\xbe", "Expected universal Mach-O")
    count = struct.unpack_from(">I", raw, 4)[0]
    require(count == 2, "Expected exactly arm64 and arm64e slices")
    found = set()
    ranges = []
    for i in range(count):
        cpu, subtype, offset, size, alignment = struct.unpack_from(">5I", raw, 8 + i * 20)
        require(cpu == 0x0100000C, "Unexpected CPU type")
        require(alignment <= 20 and offset % (1 << alignment) == 0, "Unaligned fat slice")
        require(offset >= 8 + 20 * count and offset + size <= len(raw), "Invalid slice range")
        require(all(offset + size <= lo or offset >= hi for lo, hi in ranges), "Overlapping slices")
        ranges.append((offset, offset + size))
        arch = subtype & 0x00FFFFFF
        require(arch in (0, 2) and arch not in found, "Unexpected or duplicate architecture")
        found.add(arch)
        data = raw[offset:offset + size]
        magic, inner_cpu, inner_sub, kind, ncmd, cmd_size = struct.unpack_from("<6I", data)
        require(magic == 0xFEEDFACF and kind == 6, "Expected a 64-bit dylib")
        require(inner_cpu == cpu and inner_sub == subtype, "Slice architecture mismatch")
        pos = 32
        platform_ok = False
        signature = None
        dependencies = set()
        for _ in range(ncmd):
            require(pos + 8 <= 32 + cmd_size <= len(data), "Invalid load-command range")
            cmd, length = struct.unpack_from("<II", data, pos)
            require(length >= 8 and pos + length <= 32 + cmd_size, "Invalid load command")
            if cmd == 0x32:
                platform, minimum = struct.unpack_from("<II", data, pos + 8)
                platform_ok = platform == 2 and minimum == 0x00100000
            elif cmd == 0x1D:
                signature = struct.unpack_from("<II", data, pos + 8)
            elif cmd == 0x0C:
                name_offset = struct.unpack_from("<I", data, pos + 8)[0]
                require(name_offset < length, "Invalid dependency name")
                dependencies.add(data[pos + name_offset:pos + length].split(b"\0", 1)[0])
            pos += length
        require(pos == 32 + cmd_size, "Load-command size mismatch")
        require(platform_ok, "Expected device iOS with minimum version 16.0")
        require(b"/usr/lib/libobjc.A.dylib" in dependencies, "Missing Objective-C runtime dependency")
        require(signature is not None, "Missing native code signature")
        verify_signature(data, *signature)
    require(found == {0, 2}, "Missing required architecture")


if __name__ == "__main__":
    try:
        validate_binary(Path(sys.argv[1]))
    except (ValueError, IndexError, OSError, struct.error) as error:
        sys.exit(f"Binary validation failed: {error}")
    print("Validated arm64 + arm64e, iOS 16.0 and code-signature page hashes.")
