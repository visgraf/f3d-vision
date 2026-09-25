"""Internal helper for the sealed-engine compatibility facade."""
from __future__ import annotations

from importlib import import_module


def reexport_legacy(namespace: dict, legacy_name: str) -> None:
    module = import_module(legacy_name)
    public = getattr(module, "__all__", None)
    if public is None:
        public = [name for name in dir(module) if not name.startswith("_")]
    namespace["__legacy_module__"] = legacy_name
    namespace["_legacy_impl"] = module
    namespace["__all__"] = list(public)
    for name in public:
        namespace[name] = getattr(module, name)
