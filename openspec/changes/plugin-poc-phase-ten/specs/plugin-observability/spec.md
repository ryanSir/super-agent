## ADDED Requirements

### Requirement: Runtime Event Log

The POC SHALL write runtime events for supported capability invocations.

#### Scenario: Successful invocation

- **WHEN** a capability invocation succeeds
- **THEN** the runtime event SHALL include runtime, capability id, success and duration

#### Scenario: Timeout invocation

- **WHEN** simulated delay exceeds timeout
- **THEN** invocation SHALL fail with `runtime_timeout`
- **AND** a failed runtime event SHALL be recorded
