# Data and ML Adapter

Apply this adapter to datasets, analytics, feature pipelines, model training/evaluation, ranking/recommendation metrics, and statistical outputs—even when the work is an offline script with fixed fixtures. A script entry point does not make the work a CLI/library domain unless its command interface is also part of the contract.

Ordinary offline analysis with anonymous fixtures is not automatically High-assurance. Escalate for sensitive/regulated data, production mutation, consequential model decisions, difficult rollback, or material safety/privacy risk.

Specify when applicable:

- schemas, ownership, lineage, volume, partitions, and data-quality invariants;
- dataset/model/code/dependency versions and deterministic seeds;
- train/evaluation splits, leakage controls, baseline definitions, metric formulas, tie/zero/missing behavior, aggregation, and statistical tolerance;
- training-serving skew, drift, privacy/retention, reproducibility, and rollback.

Verify with:

- representative boundary/malformed/duplicate/missing/large fixtures;
- schema and data-quality checks;
- an independent metric oracle that does not reuse the implementation under test;
- dataset/model/code/config hashes and repeated clean-environment runs;
- baseline-versus-candidate comparisons with declared exact/tolerance rules;
- offline or shadow evaluation and comparable resource/performance measurements where applicable.

Never persist unnecessary sensitive raw data in evidence. Record sanitized summaries, revisions/hashes, seeds, environment, metric intervals, cleanup, and the conditions that make evidence stale.
