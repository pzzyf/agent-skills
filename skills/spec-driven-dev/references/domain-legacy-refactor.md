# Legacy and Refactor Adapter

Apply this adapter to existing systems, refactors, and behavior changes inside previously shipped code.

Begin with an impact scan across callers, consumers, tests, manifests, ADRs, dependencies, data, and operational behavior. Classify the work:

- **Behavior-preserving refactor:** capture characterization/contract tests and observable baselines; avoid inventing product requirements.
- **Behavior change:** create or amend requirements, spec, and acceptance; run normal confirmation gates.
- **Unknown legacy behavior:** record the uncertainty and use a spike or characterization evidence before treating it as intended.

Verify with focused characterization tests, consumer/compatibility checks, and the relevant actual runtime effects. Review impacted context, not only the textual delta. Mark prior evidence stale when covered paths or assumptions change even when intended behavior remains constant.

Use Lite only for one provable impact domain with easy rollback. Upgrade to Standard for cross-module or broad mechanical changes.
