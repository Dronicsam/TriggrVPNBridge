#!/bin/bash
# SPDX-License-Identifier: MIT
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ "$(uname -s)" != Darwin ]; then
    printf '%s\n' 'Build on macOS with Apple Command Line Tools (xcode-select --install).' >&2
    exit 1
fi
xcrun --find clang >/dev/null
xcrun --find lipo >/dev/null
mkdir -p build
rm -f build/TriggrVPNBridge.dylib
for ARCH in arm64 arm64e; do
    # No SDK headers are used. Override xcrun's macOS SDK default explicitly.
    xcrun clang -target "$ARCH-apple-ios16.0" -isysroot / -dynamiclib -nostdlib -O2 \
        -Wall -Wextra -Werror -fno-stack-protector \
        -L"$ROOT/linker-stubs" -lSystem -lobjc -lFoundation -lCoreFoundation \
        -Wl,-install_name,/var/jb/Library/MobileSubstrate/DynamicLibraries/TriggrVPNBridge.dylib \
        src/TriggrVPNBridge.c -o "build/bridge-$ARCH.dylib"
done
xcrun lipo -create build/bridge-arm64.dylib build/bridge-arm64e.dylib \
    -output build/TriggrVPNBridge.dylib
codesign --force --sign - build/TriggrVPNBridge.dylib
codesign --verify --strict --all-architectures build/TriggrVPNBridge.dylib
python3 scripts/check_binary.py build/TriggrVPNBridge.dylib
printf '%s\n' 'Build complete: build/TriggrVPNBridge.dylib'
