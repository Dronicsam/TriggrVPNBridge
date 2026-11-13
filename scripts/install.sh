#!/bin/bash
# SPDX-License-Identifier: MIT
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEVICE="${1:-}"
if [[ ! "$DEVICE" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]*@[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]; then
    printf '%s\n' 'Usage: make install DEVICE=mobile@IPHONE_IP' >&2
    exit 64
fi
VERSION="$(tr -d '\n' < "$ROOT/VERSION")"
PACKAGE="$ROOT/dist/local.triggrvpnbridge_${VERSION}_iphoneos-arm64.deb"
if [ ! -f "$PACKAGE" ]; then
    printf '%s\n' 'Build the package first: make package' >&2
    exit 1
fi
scp "$PACKAGE" "$DEVICE:/var/mobile/TriggrVPNBridge.deb"
ssh -t "$DEVICE" 'sudo apt install /var/mobile/TriggrVPNBridge.deb'
printf '%s\n' 'Respring on the phone, then test: triggr-vpn toggle'
