# Validation record

## Confirmed prototype

The device owner reported successful VPN switching from SSH and from Triggr.
The bridge returned status 1 after loading and status 101 after requesting VPN on.

| Item | Confirmed configuration |
|---|---|
| Device | iPhone 12 (`iPhone13,2`) |
| OS | iOS 16.1.2 (`20B110`) |
| Jailbreak | Dopamine 3, rootless |
| Automation | Triggr 2.1 |
| VPN client | OneXray |
| Build | Native Apple tools, arm64 + arm64e |

This is a user-reported result, not an automated test or certification.

## Current packaged beta

The following checks must be completed on the packaged beta before calling it a
tested public binary. Record actual results and the exact commit/package hash.

- [ ] Install using APT; dependencies resolve and only `/var/jb` payload paths appear.
- [ ] Respring; SpringBoard loads normally and `triggr-vpn status` returns 1.
- [ ] `toggle`, `on`, and `off` change the actual VPN state as intended.
- [ ] Explicit on/off are harmless when already in the requested state.
- [ ] VPN category appears in Triggr; all three actions work.
- [ ] Existing assignments using `notifyutil` still work.
- [ ] With no usable VPN profile, behavior is recorded and SpringBoard stays usable.
- [ ] Check lock-screen actions if they are intended to be documented as supported.
- [ ] Check rapid repeated events and document the one-second repeat guard.
- [ ] Record any On Demand / Always On reconnect behavior.
- [ ] Test a later respring and upgrade from package version 0.1.0.
- [ ] Remove the package, respring, and confirm the bridge and picker category are gone.

## Automated checks

`make check` runs shell argument/error tests, a Triggr manifest-to-action integration
test, Debian archive normalization/ownership/mode/checksum validation (including
`dpkg-deb` interoperability when available), a rejected-binary packaging check,
and a signed-page tampering test. macOS CI additionally builds/signs both slices
and verifies the resulting Mach-O before packaging.

Host tests do not emulate SpringBoard, Triggr, OneXray, or Apple's private VPN API.
Never upload VPN profiles, keys, subscriptions, or unredacted device crash reports
in a public issue.
