/* SPDX-License-Identifier: MIT */
#ifndef TRIGGR_VPN_APPLE_RUNTIME_H
#define TRIGGR_VPN_APPLE_RUNTIME_H
/* Minimal declarations keep the proven Command Line Tools build independent
 * of an iOS SDK. Linker stubs contain names, never Apple implementations. */
typedef void *Obj;
typedef const void *CFRef;
typedef unsigned char ObjBool;
extern void *dlopen(const char *, int);
extern Obj objc_getClass(const char *);
extern void *sel_registerName(const char *);
extern void objc_msgSend(void);
extern CFRef CFNotificationCenterGetDarwinNotifyCenter(void);
extern CFRef CFStringCreateWithCString(CFRef, const char *, unsigned int);
extern void CFNotificationCenterAddObserver(
    CFRef, void *, void (*)(CFRef, void *, CFRef, CFRef, CFRef), CFRef, CFRef, int);
extern void dispatch_async_f(void *, void *, void (*)(void *));
extern char _dispatch_main_q;
extern double CFAbsoluteTimeGetCurrent(void);
extern void NSLog(Obj, ...);
extern unsigned int notify_register_check(const char *, int *);
extern unsigned int notify_set_state(int, unsigned long long);
#endif
