from __future__ import annotations


class PluginPocError(Exception):
    """Base exception for plugin POC errors."""


class ValidationError(PluginPocError):
    """Raised when plugin validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


class PackageError(PluginPocError):
    """Raised when package creation fails."""


class PublishError(PluginPocError):
    """Raised when registry publishing fails."""

