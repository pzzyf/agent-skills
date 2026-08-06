# Web UI Adapter

Apply this adapter only to browser-based user interfaces. Combine it with service or data adapters when the initiative spans those domains. Add requirements; never lower core gates.

Specify when applicable:

- user flows, information architecture, interaction states, and design-system constraints;
- the user-confirmed UI foundation: reuse an existing design system, adopt a named component library, or use native/custom components. For greenfield UI this is mandatory, not a tactical default. Compare framework/version compatibility, accessibility maturity, theming/customization, bundle/runtime cost, license, maintenance health, and replacement cost; record the selected option and rejected alternatives as a `DEC-*` before finalizing the spec;
- actual state ownership, persistence/hydration, concurrency, offline, and reload behavior;
- semantic structure, labels, keyboard/focus, live announcements, contrast, reduced motion, and touch targets;
- responsive behavior at meaningful viewport and content boundaries;
- loading, empty, error, partial, stale, unauthorized, and retry states.

Verify with the strongest applicable mix:

- pure behavior/unit tests and component/interaction tests;
- real browser flows for success and error paths;
- accessibility inspection and keyboard operation;
- visually inspected screenshots at representative viewports and with long/localized content;
- persistence/reload, race, and cross-session checks when storage exists.

Treat screenshots as evidence only after inspecting them. Record browser/runtime, viewport, route/state, expected/actual result, artifact path/hash, and cleanup. Derive persistence invariants from the real architecture; do not assume React, localStorage, or a particular hydration model.

For phase planning, use user-reviewable vertical slices. A typical CRUD interface should expose and pause after a first usable create/read slice, then after coherent state-change/edit behavior, and separately before or after destructive/persistence/recovery behavior as risk requires. Do not prescribe these exact groups when the product differs, but never place every core journey into one phase merely because they share a screen.
