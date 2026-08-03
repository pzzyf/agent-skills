# Infrastructure Adapter

Apply this adapter to infrastructure-as-code, cloud resources, deployment systems, and production operations. Treat production infrastructure as High-assurance.

Specify:

- exact accounts/environments/regions, desired state, ownership, dependency graph, and drift expectations;
- access policy, secrets, network exposure, quotas, cost, state/lock, and blast radius;
- plan/apply separation, rollout order, health gates, rollback, and disaster recovery;
- observability, alerts, runbooks, and post-change verification.

Verify with syntax/static/policy checks, a plan/dry-run bound to the exact configuration revision, authorized lower-environment application where appropriate, resource/state queries, health and drift checks, and rollback/recovery evidence proportional to risk.

Record that `plan != applied`. A local code-edit request never grants apply/deploy authority. Resolve exact targets before mutation, preserve unrelated resources, record provider operation IDs, and keep secrets or sensitive full plans out of evidence.
