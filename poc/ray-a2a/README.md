# Ray + A2A PoC

This directory is isolated from the main `src_deepagent` runtime. It validates whether Ray and A2A are useful before wiring either into the product path.

## What This Proves

- Ray can run local distributed-style tasks and stateful actors on one machine.
- Pydantic AI can expose an agent as an A2A ASGI server.
- A Pydantic AI agent can call a Ray-backed tool, proving the future shape:

```text
A2A client
  -> A2A server
    -> Pydantic AI agent
      -> Ray task / Ray actor
```

## Install

Use a separate virtualenv if possible.

```bash
python -m pip install -r poc/ray-a2a/requirements.txt
```

If you want to avoid changing the project environment, create a temp env:

```bash
python -m venv /tmp/ray-a2a-poc-venv
/tmp/ray-a2a-poc-venv/bin/python -m pip install -r poc/ray-a2a/requirements.txt
```

## 1. Ray Smoke Test

```bash
python poc/ray-a2a/ray_smoke.py
```

Expected behavior:

- Four 2-second tasks finish in roughly 2 seconds when enough local CPUs are available.
- A stateful Ray actor increments from `1` to `5`.
- A constrained `num_cpus=2` run executes four 2-second tasks in roughly 4 seconds.

## 2. A2A Server Smoke Test

```bash
uvicorn poc.ray-a2a.a2a_server:app --host 0.0.0.0 --port 8000
```

Python module names cannot contain hyphens, so prefer running from this directory:

```bash
cd poc/ray-a2a
uvicorn a2a_server:app --host 0.0.0.0 --port 8000
```

This uses Pydantic AI `Agent.to_a2a()` with a deterministic `TestModel`, so no LLM API key is required.

## 3. Ray-Backed A2A Agent

```bash
cd poc/ray-a2a
uvicorn ray_backed_a2a_server:app --host 0.0.0.0 --port 8001
```

This exposes an A2A server whose agent has a tool backed by a Ray remote task.

## Why This Is Separate

Ray should not be introduced into the main project until we validate a concrete bottleneck:

- many concurrent sandbox tasks,
- parallel sub-agents,
- long-running CPU/GPU workers,
- multi-machine execution,
- explicit resource scheduling,
- worker fault tolerance.

A2A is different: it is an external interoperability protocol. It can be added earlier as a protocol boundary without forcing Ray into the core runtime.

