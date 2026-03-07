from __future__ import annotations

"""Parse holon.yaml identity files."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class HolonIdentity:
    """Parsed identity from a holon.yaml file."""

    uuid: str = ""
    given_name: str = ""
    family_name: str = ""
    motto: str = ""
    composer: str = ""
    clade: str = ""
    status: str = ""
    born: str = ""
    lang: str = ""
    parents: list[str] = field(default_factory=list)
    reproduction: str = ""
    generated_by: str = ""
    proto_status: str = ""
    aliases: list[str] = field(default_factory=list)


def parse_holon(path: str | Path) -> HolonIdentity:
    """Parse a holon.yaml file and return its identity.

    Raises FileNotFoundError if the file doesn't exist.
    Raises ValueError if the YAML document is not a mapping.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: holon.yaml must be a YAML mapping")

    return HolonIdentity(
        uuid=data.get("uuid", ""),
        given_name=data.get("given_name", ""),
        family_name=data.get("family_name", ""),
        motto=data.get("motto", ""),
        composer=data.get("composer", ""),
        clade=data.get("clade", ""),
        status=data.get("status", ""),
        born=data.get("born", ""),
        lang=data.get("lang", ""),
        parents=data.get("parents", []),
        reproduction=data.get("reproduction", ""),
        generated_by=data.get("generated_by", ""),
        proto_status=data.get("proto_status", ""),
        aliases=data.get("aliases", []),
    )
