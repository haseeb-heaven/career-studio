from exporters.base import Exporter

_REGISTRY: dict[str, type] = {}


def register(fmt: str):
    def decorator(cls):
        _REGISTRY[fmt.lower()] = cls
        return cls
    return decorator


def exporter_for(fmt: str) -> Exporter:
    cls = _REGISTRY.get(fmt.lower())
    if cls is None:
        raise ValueError(f"No exporter registered for format: {fmt}")
    return cls()


# Auto-register built-in exporters
# Must come after register() is defined; importing the module triggers @register decoration.
from exporters import json_exporter as _json_exporter  # noqa: E402, F401
from exporters import csv_exporter as _csv_exporter  # noqa: E402, F401
from exporters import xml_exporter as _xml_exporter  # noqa: E402, F401
from exporters import docx_exporter as _docx_exporter  # noqa: E402, F401
from exporters import pdf_exporter as _pdf_exporter  # noqa: E402, F401
