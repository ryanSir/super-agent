## ADDED Requirements

### Requirement: Data Source Query

The POC SHALL invoke enabled `data_source` capabilities through the gateway.

#### Scenario: Query local JSON data source

- **GIVEN** a plugin with a `local_json` data source is enabled
- **WHEN** the user invokes the data source capability with a query
- **THEN** the gateway SHALL return matching records
- **AND** write audit and runtime event records
