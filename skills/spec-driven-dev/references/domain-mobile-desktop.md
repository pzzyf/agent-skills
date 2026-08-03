# Mobile and Desktop Adapter

Apply this adapter to native, hybrid, and packaged mobile/desktop applications. Add requirements; never lower core gates.

Specify when applicable:

- supported OS/device matrix, lifecycle/process death/background behavior, permissions, local data, and synchronization;
- offline/reconnect, upgrades/migrations, deep links, notifications, localization, accessibility, and input methods;
- packaging, signing, distribution, compatibility, resource, battery, performance, and crash behavior.

Verify with unit/integration tests, build/install/launch, real simulator/emulator/device flows, foreground/background/process-death, permission denial, offline/reconnect, upgrade/data preservation, accessibility, representative form factors, and crash/log inspection.

Record artifact, device/simulator, OS/runtime, and sanitized logs. Use `blocked-external` when required hardware, signing identity, entitlement, or store state is unavailable; do not claim device behavior from source review alone.
