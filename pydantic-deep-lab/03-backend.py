"""Backend demos: in-memory StateBackend vs persistent LocalBackend."""

from pathlib import Path

from pydantic_deep import LocalBackend, StateBackend


def demo_state_backend() -> None:
    print("=== StateBackend: in-memory only ===")

    backend = StateBackend()
    backend.write("/notes/state-demo.txt", "This file only lives in memory.\n")

    print(backend.read("/notes/state-demo.txt"))
    print("StateBackend files:", sorted(backend.files))
    print()


def demo_local_backend() -> None:
    print("=== LocalBackend: persistent local files ===")

    workspace = Path(__file__).parent / "backend-workspace"
    backend = LocalBackend(root_dir=workspace)
    file_path = "notes/local-demo.txt"
    backend.write(file_path, "This file is persisted on disk.\n")

    print(backend.read(file_path))
    print("LocalBackend root:", workspace)
    print("Actual file exists:", (workspace / "notes" / "local-demo.txt").exists())
    print()


def main() -> None:
    demo_state_backend()
    demo_local_backend()


if __name__ == "__main__":
    main()
