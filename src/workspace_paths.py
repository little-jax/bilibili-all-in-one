"""Workspace path resolution for the workspace-maintained Bilibili skill."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

SKILL_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_SENTINELS = ("AGENTS.md", "SOUL.md", "USER.md", "MEMORY.md")
ENV_WORKSPACE = "OPENCLAW_WORKSPACE"
ENV_ALT_WORKSPACE = "WORKSPACE"


def _candidate_roots() -> Iterable[Path]:
    for value in (os.getenv(ENV_WORKSPACE), os.getenv(ENV_ALT_WORKSPACE)):
        if value:
            yield Path(value).expanduser()
    yield Path.cwd()
    yield SKILL_ROOT
    yield SKILL_ROOT.parent
    yield SKILL_ROOT.parent.parent


def detect_workspace_root(start: str | Path | None = None) -> Path:
    seen: set[Path] = set()
    candidates = []
    if start is not None:
        candidates.append(Path(start).expanduser())
    candidates.extend(_candidate_roots())

    for candidate in candidates:
        current = candidate.resolve()
        if current.is_file():
            current = current.parent
        for probe in (current, *current.parents):
            if probe in seen:
                continue
            seen.add(probe)
            if all((probe / marker).exists() for marker in WORKSPACE_SENTINELS):
                return probe
    raise RuntimeError(
        "Could not detect OpenClaw workspace root for bilibili-all-in-one; set OPENCLAW_WORKSPACE or WORKSPACE."
    )


def workspace_path(*parts: str, start: str | Path | None = None) -> Path:
    return detect_workspace_root(start=start).joinpath(*parts)
