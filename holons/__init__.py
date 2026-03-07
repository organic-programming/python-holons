"""holons — Organic Programming SDK for Python."""

from importlib import import_module

__all__ = ["transport", "serve", "identity", "discover", "grpcclient", "holonrpc"]


def __getattr__(name: str):
    if name in __all__:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
