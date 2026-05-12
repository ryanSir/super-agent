## Design

Runtime Host state is stored in `runtime_host.json` under the POC state directory.

Starting a runtime records:

- plugin id and version
- mode
- running status
- health
- stdio adapter endpoint mappings

The adapter does not spawn subprocesses yet. It validates the configuration shape needed for a later daemon implementation.
