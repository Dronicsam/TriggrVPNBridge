# Triggr VPN Bridge

Toggle the selected iOS VPN from **Triggr**, without Shortcuts or opening the VPN app.

[Русский](README.ru.md) · [Build](docs/BUILDING.md) · [Testing](docs/TESTING.md)

**Beta source release.** The native-built prototype was confirmed working on an
iPhone 12, iOS 16.1.2, Dopamine 3, Triggr 2.1 and OneXray. The packaged beta and
action-picker integration still need the device checks in [TESTING.md](docs/TESTING.md).

## Features

- Toggle, turn on, or turn off the selected system VPN.
- A **VPN** category in Triggr's action picker, using its documented extension format.
- A small `triggr-vpn` shell command and existing Darwin notification commands.
- A status code for diagnosis, selector checks, and a one-second repeat guard.
- SpringBoard-only loading; no polling, network listener, or analytics.

The bridge does not require CCVPN or OneXray. It controls the system-selected VPN,
not a named profile or server inside an app. Other VPN clients have not been tested.
CCVPN can remain installed alongside it.

## Compatibility

| Component | Status |
|---|---|
| iOS 16.1.2 / iPhone 12 | Prototype confirmed by the device owner |
| Dopamine 3 / Triggr 2.1 / OneXray | Prototype confirmed by the device owner |
| Other iOS 16 devices and VPN clients | Targeted, untested |
| iOS 15, iOS 17+, RootHide, rootful jailbreaks | Unsupported by this package |
| New VPN action-picker category | Implemented; device validation pending |

Package architecture is `iphoneos-arm64`; the dylib contains **arm64 + arm64e**.

## Install

Download a beta `.deb` from a build artifact or build it yourself:

```sh
make check
make package
make install DEVICE=mobile@IPHONE_IP
```

The package depends on `notifyutil` from Procursus and ElleKit. The installer uses
APT to resolve dependencies. Respring after installing or removing the package.

For a downloaded package, copy it to the phone, then run there:

```sh
sudo apt install /var/mobile/TriggrVPNBridge.deb
sudo sbreload
```

## Use in Triggr

Select a trigger, open the **VPN** category, and choose **Toggle VPN**,
**Turn VPN On**, or **Turn VPN Off**. The category is installed automatically.

If your Triggr version does not display it, select **Text & Commands → Run Command**:

```sh
/var/jb/usr/bin/triggr-vpn toggle
```

Use `on` or `off` for an explicit action. Commands run as `mobile`; no `sudo` needed.

Existing assignments also remain valid:

```sh
/var/jb/usr/bin/notifyutil -p local.triggrvpnbridge.toggle
/var/jb/usr/bin/notifyutil -p local.triggrvpnbridge.on
/var/jb/usr/bin/notifyutil -p local.triggrvpnbridge.off
```

## Diagnose

```sh
triggr-vpn status
triggr-vpn toggle
# Wait at least one second, then read status again.
triggr-vpn status
```

| Code | Meaning |
|---|---|
| 0 / no value | No status published; check installation and respring |
| 1 | Bridge initialized |
| 2 | Handling a request |
| 3 | Request ignored by the one-second repeat guard |
| 10 | Could not load VPNPreferences |
| 11 | VPNBundleController unavailable |
| 12 | Controller initialization failed |
| 13 | Expected VPN methods unavailable |
| 14 | Could not read VPN state |
| 100 / 101 | Requested off / on; not confirmation of connection |
| 200 / 201 | VPN reported already off / on |

Status is the **last published diagnostic**, not live tunnel state or a liveness
check. Confirm the VPN indicator or Settings state yourself. A successful command
exit only means the notification was posted/read. On Demand or Always On may
reconnect after an off request. Do not send command bursts: notifications can
coalesce, and requests within one second of a change are ignored.

## Remove

```sh
sudo apt remove local.triggrvpnbridge
sudo sbreload
```

If SpringBoard enters Safe Mode, remove the package in Sileo or over SSH and respring.

## How it works

A filtered dylib listens for three local Darwin notifications and dispatches VPN
work to SpringBoard's main queue. It dynamically loads Apple's `VPNPreferences`
bundle, creates `VPNBundleController`, reads `vpnActiveForSpecifier:`, and calls
`setVPNActive:`. These are private APIs and may change between iOS releases.

Darwin notifications carry no authenticated sender. **Other local processes may
invoke these VPN actions.** The bridge is not a VPN kill switch or a security
boundary. It does not read, log or export VPN credentials or traffic.

## Credits and license

By [Andrey Samokhvalov](https://github.com/Dronicsam). MIT license; see [LICENSE](LICENSE).

- [Triggr](https://github.com/Jond-ie/triggr) and its
  [extension format](https://github.com/Jond-ie/triggr/blob/main/EXTENSIONS.md).
- CCVPN by KingPuffDaddi: its behavior helped identify the system VPN API sequence.
  No CCVPN binary or source is included in this repository.
- Apple runtime and system framework APIs. Linker stubs contain declarations only;
  no Apple SDK or framework implementation is redistributed.
