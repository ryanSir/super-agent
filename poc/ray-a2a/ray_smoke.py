"""Local Ray smoke tests.

Run:
    python poc/ray-a2a/ray_smoke.py
"""

from __future__ import annotations

import time

try:
    import ray
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "Missing dependency: ray. Install with `python -m pip install -r poc/ray-a2a/requirements.txt`."
    ) from exc


@ray.remote
def slow_task(index: int) -> str:
    time.sleep(2)
    return f"task-{index}"


@ray.remote
class CounterActor:
    def __init__(self) -> None:
        self.value = 0

    def increment(self) -> int:
        self.value += 1
        return self.value


@ray.remote(num_cpus=1)
def cpu_limited_task(index: int) -> int:
    time.sleep(2)
    return index


def run_parallel_task_demo() -> None:
    start = time.time()
    refs = [slow_task.remote(i) for i in range(4)]
    results = ray.get(refs)
    elapsed = time.time() - start
    print("parallel task results:", results)
    print("parallel task elapsed:", round(elapsed, 2), "seconds")


def run_actor_demo() -> None:
    counter = CounterActor.remote()
    refs = [counter.increment.remote() for _ in range(5)]
    print("actor increments:", ray.get(refs))


def run_resource_demo() -> None:
    ray.shutdown()
    ray.init(num_cpus=2)

    start = time.time()
    refs = [cpu_limited_task.remote(i) for i in range(4)]
    results = ray.get(refs)
    elapsed = time.time() - start
    print("resource-limited results:", results)
    print("resource-limited elapsed:", round(elapsed, 2), "seconds")


def main() -> None:
    ray.init(ignore_reinit_error=True)
    print("ray resources:", ray.cluster_resources())
    run_parallel_task_demo()
    run_actor_demo()
    run_resource_demo()
    ray.shutdown()


if __name__ == "__main__":
    main()

