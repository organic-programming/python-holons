from __future__ import annotations

"""Discover holons by scanning for holon.yaml manifests."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
import os

import yaml

from .identity import HolonIdentity, parse_holon


@dataclass
class HolonBuild:
    runner: str = ""
    main: str = ""


@dataclass
class HolonArtifacts:
    binary: str = ""
    primary: str = ""


@dataclass
class HolonManifest:
    kind: str = ""
    build: HolonBuild = field(default_factory=HolonBuild)
    artifacts: HolonArtifacts = field(default_factory=HolonArtifacts)


@dataclass
class HolonEntry:
    slug: str
    uuid: str
    dir: str
    relative_path: str
    origin: str
    identity: HolonIdentity
    manifest: HolonManifest | None


def discover(root: str | Path) -> list[HolonEntry]:
    return _discover_in_root(Path(root), "local")


def discover_local() -> list[HolonEntry]:
    return discover(Path.cwd())


def discover_all() -> list[HolonEntry]:
    entries: list[HolonEntry] = []
    seen: set[str] = set()
    for root, origin in (
        (Path.cwd(), "local"),
        (_opbin(), "$OPBIN"),
        (_cache_dir(), "cache"),
    ):
        for entry in _discover_in_root(root, origin):
            key = entry.uuid.strip() or entry.dir
            if key in seen:
                continue
            seen.add(key)
            entries.append(entry)
    return entries


def find_by_slug(slug: str) -> HolonEntry | None:
    needle = slug.strip()
    if not needle:
        return None

    match: HolonEntry | None = None
    for entry in discover_all():
        if entry.slug != needle:
            continue
        if match is not None and match.uuid != entry.uuid:
            raise ValueError(f'ambiguous holon "{needle}"')
        match = entry
    return match


def find_by_uuid(prefix: str) -> HolonEntry | None:
    needle = prefix.strip()
    if not needle:
        return None

    match: HolonEntry | None = None
    for entry in discover_all():
        if not entry.uuid.startswith(needle):
            continue
        if match is not None and match.uuid != entry.uuid:
            raise ValueError(f'ambiguous UUID prefix "{needle}"')
        match = entry
    return match


def _discover_in_root(root: Path, origin: str) -> list[HolonEntry]:
    root = (root if str(root).strip() else Path.cwd()).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return []

    entries_by_key: dict[str, HolonEntry] = {}
    ordered_keys: list[str] = []
    _scan_dir(root, root, origin, entries_by_key, ordered_keys)

    entries = [entries_by_key[key] for key in ordered_keys if key in entries_by_key]
    entries.sort(key=lambda entry: (entry.relative_path, entry.uuid))
    return entries


def _scan_dir(
    root: Path,
    current: Path,
    origin: str,
    entries_by_key: dict[str, HolonEntry],
    ordered_keys: list[str],
) -> None:
    try:
        children = list(current.iterdir())
    except OSError:
        return

    for child in children:
        name = child.name
        if child.is_dir():
            if _should_skip_dir(root, child, name):
                continue
            _scan_dir(root, child, origin, entries_by_key, ordered_keys)
            continue
        if not child.is_file() or name != "holon.yaml":
            continue

        try:
            identity = parse_holon(child)
            manifest = _parse_manifest(child)
        except Exception:
            continue

        holon_dir = child.parent.resolve()
        entry = HolonEntry(
            slug=_slug_for(identity),
            uuid=identity.uuid,
            dir=str(holon_dir),
            relative_path=_relative_path(root, holon_dir),
            origin=origin,
            identity=identity,
            manifest=manifest,
        )
        key = entry.uuid.strip() or entry.dir
        existing = entries_by_key.get(key)
        if existing is not None:
            if _path_depth(entry.relative_path) < _path_depth(existing.relative_path):
                entries_by_key[key] = entry
            continue

        entries_by_key[key] = entry
        ordered_keys.append(key)


def _parse_manifest(path: Path) -> HolonManifest:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: holon.yaml must be a YAML mapping")

    build = data.get("build")
    artifacts = data.get("artifacts")
    build_map = build if isinstance(build, dict) else {}
    artifacts_map = artifacts if isinstance(artifacts, dict) else {}

    return HolonManifest(
        kind=str(data.get("kind", "")),
        build=HolonBuild(
            runner=str(build_map.get("runner", "")),
            main=str(build_map.get("main", "")),
        ),
        artifacts=HolonArtifacts(
            binary=str(artifacts_map.get("binary", "")),
            primary=str(artifacts_map.get("primary", "")),
        ),
    )


def _slug_for(identity: HolonIdentity) -> str:
    given = identity.given_name.strip()
    family = identity.family_name.strip().removesuffix("?")
    if not given and not family:
        return ""
    return f"{given}-{family}".strip().lower().replace(" ", "-").strip("-")


def _should_skip_dir(root: Path, path: Path, name: str) -> bool:
    if path == root:
        return False
    return name in {".git", ".op", "node_modules", "vendor", "build"} or name.startswith(".")


def _relative_path(root: Path, holon_dir: Path) -> str:
    try:
        rel = holon_dir.relative_to(root)
        return "." if str(rel) == "." else rel.as_posix()
    except ValueError:
        return holon_dir.as_posix()


def _path_depth(relative_path: str) -> int:
    trimmed = relative_path.strip().strip("/")
    if not trimmed or trimmed == ".":
        return 0
    return len(trimmed.split("/"))


def _op_path() -> Path:
    configured = os.environ.get("OPPATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.home().joinpath(".op")


def _opbin() -> Path:
    configured = os.environ.get("OPBIN", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _op_path().joinpath("bin")


def _cache_dir() -> Path:
    return _op_path().joinpath("cache")
