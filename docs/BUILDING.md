# Build and release

Use **macOS + Apple Command Line Tools**, Python 3.9 or newer, and `make`.
No Homebrew dependencies, full Xcode, downloaded iOS SDK, or Theos are required.
The native Apple build path was used for the prototype confirmed on the phone.

```sh
xcode-select --install  # Only if Command Line Tools are missing.
make check
make package
```

`scripts/build.sh` compiles the dylib twice (arm64/arm64e), combines the slices with
`lipo`, ad-hoc signs with Apple's `codesign`, verifies the signature, then validates
the iOS deployment target and signed page hashes. Do not substitute the old Linux
prototype build or custom signature code: those artifacts failed on the test phone.

The C bridge deliberately uses small runtime declarations and symbol-only TAPI
stubs. The private class is resolved at runtime. The stubs are not implementations
and are not shipped inside the `.deb`.

`scripts/package.py` validates the dylib again and creates an `iphoneos-arm64`
Debian package using only Python's standard library. It normalizes archive owners,
modes, file order, timestamps, and gzip metadata; includes payload MD5 checksums;
and writes a separate SHA-256 checksum. Set `SOURCE_DATE_EPOCH` for an explicit
timestamp. Archive assembly is deterministic for identical signed binary bytes;
this is not a promise that Apple's native build is bit-for-bit reproducible.

Only rootless `/var/jb` paths are installed. The package ID remains
`local.triggrvpnbridge` to upgrade the working prototype without two bridge copies.
The native helper executable was replaced by a shell wrapper around the package
dependency `notifyutil`.

## Install on a test phone

```sh
make install DEVICE=mobile@IPHONE_IP
```

This explicitly copies a `.deb` to `/var/mobile/TriggrVPNBridge.deb`, installs it
with `sudo apt install`, and asks you to respring. Build and package commands alone
never contact a device. No address or credentials are stored in this repository.

## GitHub Actions

The build workflow runs host checks and the native macOS build, then uploads the
`.deb` and SHA-256 file as a workflow artifact. It has read-only repository
permissions, does not run phone commands, and does not publish releases.

## First public beta

1. Pass the build workflow.
2. Complete and record [device checks](TESTING.md) for the packaged beta.
3. Keep unverified compatibility claims marked as untested.
4. Use `v0.2.0-beta1` as the tag for Debian version `0.2.0~beta1`.
5. Attach the checked `.deb` and checksum to a prerelease with the validation notes.

Do not label the source release or an Actions artifact as device-tested solely
because the older prototype worked.
