# Changelog

## 0.2.0~beta1

- Prepare the working prototype as a source repository and rootless Debian package.
- Add a Triggr VPN action category and strict shell action dispatch.
- Replace the native CLI helper with a wrapper around Procursus `notifyutil`.
- Keep existing package and notification identifiers for upgrades.
- Use Apple tools for universal builds and native ad-hoc signatures.
- Validate architecture, deployment target and code-signature hashes before packaging.
- Add host tests, macOS build automation, English/Russian documentation and MIT license.
- Preserve the system VPN API sequence and one-second repeat guard.
- Mark packaged-beta and picker validation as pending rather than reusing prototype claims.

## Prototype

- The device owner confirmed the native-built bridge toggled OneXray from Triggr
  on iOS 16.1.2 with Dopamine 3.
