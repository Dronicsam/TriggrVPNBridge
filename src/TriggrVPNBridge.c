/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 Andrey Samokhvalov and contributors
 * SpringBoard only; private VPN calls run on its main queue.
 * No hooks, swizzling, polling, networking or credential reads.
 */
#include "AppleRuntime.h"
#include "BridgeProtocol.h"

static Obj controller;
static int statusToken = -1;
static double lastRequestTime;

static void setStatus(enum VPNStatus value) {
    if (statusToken >= 0) notify_set_state(statusToken, (unsigned long long)value);
}
static Obj send(Obj object, const char *selector) {
    return ((Obj (*)(Obj, void *))objc_msgSend)(object, sel_registerName(selector));
}
static Obj sendObject(Obj object, const char *selector, Obj argument) {
    return ((Obj (*)(Obj, void *, Obj))objc_msgSend)(object, sel_registerName(selector), argument);
}
static ObjBool responds(Obj object, const char *selector) {
    return ((ObjBool (*)(Obj, void *, void *))objc_msgSend)(
        object, sel_registerName("respondsToSelector:"), sel_registerName(selector));
}
static void logMessage(const char *message) {
    Obj cls = objc_getClass("NSString");
    Obj text = sendObject(cls, "stringWithUTF8String:", (Obj)message);
    Obj format = sendObject(cls, "stringWithUTF8String:", (Obj)"[TriggrVPNBridge] %@");
    NSLog(format, text);
}
static int prepareController(void) {
    if (controller) return 1;
    /* RTLD_NOW = 2. Keep the handle open while controller is retained. */
    if (!dlopen("/System/Library/PreferenceBundles/VPNPreferences.bundle/VPNPreferences", 2)) {
        setStatus(VPN_LOAD_ERROR); logMessage("Could not load VPNPreferences"); return 0;
    }
    Obj cls = objc_getClass("VPNBundleController");
    if (!cls || !responds(cls, "alloc")) {
        setStatus(VPN_CLASS_ERROR); logMessage("VPNBundleController unavailable"); return 0;
    }
    Obj instance = send(cls, "alloc");
    if (!instance || !responds(instance, "initWithParentListController:")) {
        send(instance, "release");
        setStatus(VPN_INIT_ERROR); logMessage("Unexpected VPN controller initializer"); return 0;
    }
    controller = sendObject(instance, "initWithParentListController:", 0);
    if (!controller) {
        setStatus(VPN_INIT_ERROR); logMessage("VPN controller initialization failed"); return 0;
    }
    return 1;
}
static void perform(void *context) {
    enum VPNAction action = (enum VPNAction)((unsigned long)context - 1);
    if (action < VPN_TOGGLE || action > VPN_OFF) return;
    /* Preserve the prototype's one-second protection against repeated triggers.
     * Darwin notifications are not a reliable queue for rapid command bursts. */
    double now = CFAbsoluteTimeGetCurrent();
    if (lastRequestTime > 0 && now >= lastRequestTime && now - lastRequestTime < 1.0) {
        setStatus(VPN_THROTTLED); return;
    }
    setStatus(VPN_HANDLING);
    Obj pool = send(send(objc_getClass("NSAutoreleasePool"), "alloc"), "init");
    if (!prepareController()) goto done;
    if (!responds(controller, "vpnActiveForSpecifier:") || !responds(controller, "setVPNActive:")) {
        setStatus(VPN_METHOD_ERROR); logMessage("Required VPN methods unavailable"); goto done;
    }
    Obj value = sendObject(controller, "vpnActiveForSpecifier:", 0);
    if (!value || !responds(value, "boolValue")) {
        setStatus(VPN_STATE_ERROR); logMessage("Could not read VPN state"); goto done;
    }
    ObjBool active = ((ObjBool (*)(Obj, void *))objc_msgSend)(value, sel_registerName("boolValue"));
    ObjBool desired = action == VPN_ON ? 1 : action == VPN_OFF ? 0 : !active;
    if (desired == active) {
        setStatus(desired ? VPN_ALREADY_ON : VPN_ALREADY_OFF); goto done;
    }
    lastRequestTime = now;
    ((void (*)(Obj, void *, ObjBool))objc_msgSend)(controller, sel_registerName("setVPNActive:"), desired);
    /* An API call was made; this does not confirm a connected tunnel. */
    setStatus(desired ? VPN_REQUESTED_ON : VPN_REQUESTED_OFF);
    logMessage(desired ? "Requested VPN on" : "Requested VPN off");
done:
    send(pool, "drain");
}
static void received(CFRef center, void *context, CFRef name, CFRef object, CFRef info) {
    (void)center; (void)name; (void)object; (void)info;
    dispatch_async_f(&_dispatch_main_q, context, perform);
}
__attribute__((constructor)) static void initialize(void) {
    if (notify_register_check(VPN_NOTIFY_STATUS, &statusToken) != 0) statusToken = -1;
    const char *names[] = { VPN_NOTIFY_TOGGLE, VPN_NOTIFY_ON, VPN_NOTIFY_OFF };
    CFRef center = CFNotificationCenterGetDarwinNotifyCenter();
    for (unsigned long i = 0; i < 3; i++) {
        CFRef name = CFStringCreateWithCString(0, names[i], 0x08000100); /* UTF-8 */
        if (name) {
            CFNotificationCenterAddObserver(center, (void *)(i + 1), received,
                                            name, 0, 4); /* DeliverImmediately */
        }
        /* Keep the three names alive for the process lifetime. */
    }
    setStatus(VPN_LOADED);
}
