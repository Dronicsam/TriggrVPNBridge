/* SPDX-License-Identifier: MIT */
#ifndef TRIGGR_VPN_BRIDGE_PROTOCOL_H
#define TRIGGR_VPN_BRIDGE_PROTOCOL_H
/* Retain the prototype's names so existing assignments keep working. */
#define VPN_NOTIFY_TOGGLE "local.triggrvpnbridge.toggle"
#define VPN_NOTIFY_ON     "local.triggrvpnbridge.on"
#define VPN_NOTIFY_OFF    "local.triggrvpnbridge.off"
#define VPN_NOTIFY_STATUS "local.triggrvpnbridge.status"
enum VPNAction { VPN_TOGGLE, VPN_ON, VPN_OFF };
enum VPNStatus {
    VPN_LOADED = 1, VPN_HANDLING = 2, VPN_THROTTLED = 3,
    VPN_LOAD_ERROR = 10, VPN_CLASS_ERROR = 11, VPN_INIT_ERROR = 12,
    VPN_METHOD_ERROR = 13, VPN_STATE_ERROR = 14,
    VPN_REQUESTED_OFF = 100, VPN_REQUESTED_ON = 101,
    VPN_ALREADY_OFF = 200, VPN_ALREADY_ON = 201
};
#endif
