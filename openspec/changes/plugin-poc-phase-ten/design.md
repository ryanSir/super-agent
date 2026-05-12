## Design

Runtime events are separate from audit logs:

- audit log answers who did what
- runtime event log answers how the runtime behaved

For POC stability, timeout behavior is simulated with `simulate_delay_ms` input and `--timeout-ms`.
