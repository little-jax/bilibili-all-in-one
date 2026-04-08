"""Configuration loader for Bilibili automation-facing features."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from .workspace_paths import SKILL_ROOT, workspace_path

DEFAULT_MESSAGE_CENTER_CONFIG = workspace_path("bilibili-message-center.json")
TEMPLATE_MESSAGE_CENTER_CONFIG = SKILL_ROOT / "config" / "message-center.example.json"
ENV_MESSAGE_CENTER_CONFIG = "BILIBILI_MESSAGE_CENTER_CONFIG"


def _config_path() -> Path:
    override = os.getenv(ENV_MESSAGE_CENTER_CONFIG)
    if override:
        return Path(override).expanduser()
    if DEFAULT_MESSAGE_CENTER_CONFIG.exists():
        return DEFAULT_MESSAGE_CENTER_CONFIG
    return TEMPLATE_MESSAGE_CENTER_CONFIG


def load_message_center_config() -> Dict[str, Any]:
    path = _config_path()
    if not path.exists():
        return {
            "digest": {"maxItems": 5, "previewLength": 100},
            "automation": {"minPriorityToNotify": 80},
            "priorityRules": [],
            "notificationRoutes": [],
            "_meta": {
                "source": str(path),
                "defaultPath": str(DEFAULT_MESSAGE_CENTER_CONFIG),
                "templatePath": str(TEMPLATE_MESSAGE_CENTER_CONFIG),
                "exists": False,
            },
        }

    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("digest", {"maxItems": 5, "previewLength": 100})
    data.setdefault("automation", {"minPriorityToNotify": 80})
    data.setdefault("priorityRules", [])
    data.setdefault("notificationRoutes", [])
    data["_meta"] = {
        "source": str(path),
        "defaultPath": str(DEFAULT_MESSAGE_CENTER_CONFIG),
        "templatePath": str(TEMPLATE_MESSAGE_CENTER_CONFIG),
        "exists": True,
    }
    return data
