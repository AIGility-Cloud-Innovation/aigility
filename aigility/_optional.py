"""Helpers for loading optional dependencies at feature-use seams."""

from importlib import import_module
from types import ModuleType
from typing import Optional


class MissingOptionalDependencyError(ImportError):
    """An optional dependency required by an explicitly used feature is absent."""


def import_optional(
    module_name: str,
    *,
    feature: str,
    extra: str,
    dependency: Optional[str] = None,
) -> ModuleType:
    """Import an optional module and report the matching AIGility extra.

    Only a missing requested module is translated. Import errors raised from inside an
    installed dependency retain their original traceback and message.
    """

    try:
        return import_module(module_name)
    except ModuleNotFoundError as exc:
        missing = exc.name or ""
        parts = module_name.split(".")
        requested_chain = {
            ".".join(parts[:index]) for index in range(1, len(parts) + 1)
        }
        if missing not in requested_chain:
            raise

        requested_root = parts[0]
        package_name = dependency or requested_root.replace("_", "-")
        raise MissingOptionalDependencyError(
            f"{feature} requires optional dependency '{package_name}'.\n"
            f'Install with: pip install "aigility[{extra}]"'
        ) from exc


__all__ = ["MissingOptionalDependencyError", "import_optional"]
