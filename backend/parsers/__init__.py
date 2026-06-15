from parsers.base import ParseResult

_REGISTRY: dict[str, type] = {}


def register(ext: str):
    def decorator(cls):
        _REGISTRY[ext.lower()] = cls
        return cls
    return decorator


def parser_for(ext: str):
    cls = _REGISTRY.get(ext.lower())
    if cls is None:
        raise ValueError(f"No parser registered for extension: {ext}")
    return cls()


# Must come after register() is defined; importing the module triggers @register decoration.
# Add one line per parser as they are implemented in later tasks:
from parsers import json_parser as _json_parser  # noqa: E402, F401
from parsers import csv_parser as _csv_parser  # noqa: E402, F401
from parsers import xml_parser as _xml_parser  # noqa: E402, F401
from parsers import docx_parser as _docx_parser  # noqa: E402, F401
from parsers import pdf_parser as _pdf_parser  # noqa: E402, F401
from parsers import tex_parser as _tex_parser  # noqa: E402, F401
