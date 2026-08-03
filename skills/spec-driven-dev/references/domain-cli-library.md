# CLI and Library Adapter

Apply this adapter to command-line tools, packages, SDKs, and reusable libraries when their public invocation, output, packaging, or consumer contract is in scope. Do not select it merely because an internal data/ML script happens to run from a shell. Add requirements; never lower core gates.

Specify when applicable:

- command/API surface, input grammar, defaults, configuration precedence, exit codes, stdout/stderr, TTY/signals, and file effects;
- install/runtime/platform/version support;
- partial writes, cancellation, atomicity, and cleanup;
- API/ABI/semantic-version compatibility and migration expectations.

Verify with:

- unit/property tests for deterministic logic;
- invocation or import from a clean temporary consumer project;
- stdout/stderr, exit-code, filesystem, signal, and error-path assertions;
- packaging/install/import checks and package hashes;
- multiple supported runtime/platform versions when required;
- executable documentation examples where practical.

Do not force UI, browser, persistence, or language-specific interface sections. Treat public compatibility or packaging changes as significant when they create consumer migration cost or ecosystem lock-in.
