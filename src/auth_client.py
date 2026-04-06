"""Productized auth workflows for Bilibili login/session management."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import qrcode

from .auth import BilibiliAuth
from .utils import DEFAULT_HEADERS, API_BASE

PASSPORT_BASE = "https://passport.bilibili.com"
QR_GENERATE_URL = f"{PASSPORT_BASE}/x/passport-login/web/qrcode/generate"
QR_POLL_URL = f"{PASSPORT_BASE}/x/passport-login/web/qrcode/poll"

SKILL_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = SKILL_ROOT / ".runtime"
QR_SESSION_FILE = RUNTIME_DIR / "qr-login-session.json"
QR_IMAGE_FILE = RUNTIME_DIR / "qr-login.png"
QR_HTML_FILE = RUNTIME_DIR / "qr-login.html"


class BilibiliAuthClient:
    """Higher-level auth workflows with QR-first login UX."""

    def __init__(self, auth: Optional[BilibiliAuth] = None):
        self.auth = auth or BilibiliAuth()

    def _ensure_runtime_dir(self) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    def _write_json_secure(self, path: Path, payload: Dict[str, Any]) -> None:
        self._ensure_runtime_dir()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _render_qr_assets(self, url: str) -> Dict[str, str]:
        self._ensure_runtime_dir()
        qr = qrcode.QRCode(border=2, box_size=8)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(QR_IMAGE_FILE)

        from io import StringIO
        buf = StringIO()
        qr.print_ascii(out=buf)
        ascii_qr = buf.getvalue()

        image_b64 = base64.b64encode(QR_IMAGE_FILE.read_bytes()).decode("ascii")
        html = f"""<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Bilibili QR Login</title>
    <style>
      body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 24px; background: #111; color: #eee; }}
      .card {{ max-width: 720px; margin: 0 auto; padding: 24px; border-radius: 16px; background: #1b1b1b; }}
      img {{ background: white; padding: 12px; border-radius: 12px; width: min(92vw, 420px); height: auto; }}
      code, pre {{ white-space: pre-wrap; word-break: break-word; }}
      a {{ color: #8ab4ff; }}
    </style>
  </head>
  <body>
    <div class=\"card\">
      <h1>Bilibili QR Login</h1>
      <p>Use the Bilibili app to scan this QR code. Default flow: send/display the PNG directly. This page is just a local fallback.</p>
      <p><img src=\"data:image/png;base64,{image_b64}\" alt=\"Bilibili QR login\" /></p>
      <p><strong>Scan URL</strong></p>
      <p><code>{url}</code></p>
      <details>
        <summary>ASCII fallback</summary>
        <pre>{ascii_qr}</pre>
      </details>
    </div>
  </body>
</html>
"""
        QR_HTML_FILE.write_text(html, encoding="utf-8")
        return {
            "image_path": str(QR_IMAGE_FILE),
            "html_path": str(QR_HTML_FILE),
            "ascii_qr": ascii_qr,
        }

    def _session_payload(self, *, qrcode_key: str, url: str) -> Dict[str, Any]:
        return {
            "qrcode_key": qrcode_key,
            "url": url,
            "image_path": str(QR_IMAGE_FILE),
            "html_path": str(QR_HTML_FILE),
        }

    async def start_qr_login(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(QR_GENERATE_URL)
            data = resp.json()

        if data.get("code") != 0:
            return {
                "success": False,
                "stage": "generate_qr",
                "error_type": "api_error",
                "message": data.get("message", "Failed to generate QR login"),
                "detail": data,
            }

        payload = data.get("data") or {}
        url = payload.get("url")
        qrcode_key = payload.get("qrcode_key")
        if not url or not qrcode_key:
            return {
                "success": False,
                "stage": "generate_qr",
                "error_type": "invalid_response",
                "message": "QR login response missing url or qrcode_key",
                "detail": payload,
            }

        assets = self._render_qr_assets(url)
        self._write_json_secure(QR_SESSION_FILE, self._session_payload(qrcode_key=qrcode_key, url=url))
        return {
            "success": True,
            "schema": "bilibili.auth_client.start_qr_login.v1",
            "mode": "qr_login",
            "default_presentation": "image",
            "message": "QR login ready. Default behavior is to send/show the PNG directly; HTML is fallback only when images are not visible in the current session.",
            "qrcode_key": qrcode_key,
            "qr_url": url,
            "image_path": assets["image_path"],
            "html_path": assets["html_path"],
            "ascii_qr": assets["ascii_qr"],
            "instructions": {
                "primary": "Open the PNG and scan it with the Bilibili app.",
                "fallback": "If images are not visible in the current session, open the local HTML file or use the raw qr_url.",
            },
            "agent_delivery": {
                "preferred": {
                    "kind": "image",
                    "path": assets["image_path"],
                    "reason": "Best operator UX. Use this first whenever the current channel supports image attachments.",
                },
                "fallbacks": [
                    {
                        "kind": "html",
                        "path": assets["html_path"],
                        "reason": "Use when the current session cannot display image attachments but can open local/browser content.",
                    },
                    {
                        "kind": "url",
                        "value": url,
                        "reason": "Raw QR login URL fallback.",
                    },
                    {
                        "kind": "ascii",
                        "value": assets["ascii_qr"],
                        "reason": "Weak fallback only; avoid as the default agent UX.",
                    },
                ],
                "policy": "Prefer direct image delivery. Do not default to ASCII unless the user explicitly cannot use image/html presentation.",
            },
            "session_file": str(QR_SESSION_FILE),
        }

    async def poll_qr_login(self, qrcode_key: Optional[str] = None, persist: Optional[bool] = None) -> Dict[str, Any]:
        if not qrcode_key:
            if not QR_SESSION_FILE.exists():
                return {
                    "success": False,
                    "stage": "load_qr_session",
                    "error_type": "missing_session",
                    "message": "No QR login session found. Run start_qr_login first.",
                }
            qrcode_key = self._read_json(QR_SESSION_FILE).get("qrcode_key")

        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(QR_POLL_URL, params={"qrcode_key": qrcode_key})
            data = resp.json()
            payload = data.get("data") or {}
            state_code = payload.get("code")

            if data.get("code") != 0:
                return {
                    "success": False,
                    "stage": "poll_qr",
                    "error_type": "api_error",
                    "message": data.get("message", "Failed to poll QR login status"),
                    "detail": data,
                }

            status_map = {
                86101: ("waiting_scan", "未扫码"),
                86090: ("waiting_confirm", "已扫码，待确认"),
                86038: ("expired", "二维码已过期"),
                0: ("success", "登录成功"),
            }
            status, default_message = status_map.get(state_code, ("unknown", payload.get("message") or "Unknown QR state"))

            if state_code == 0 and payload.get("url"):
                await client.get(payload["url"], headers={**DEFAULT_HEADERS, "Referer": "https://www.bilibili.com"})

            client_cookies = client.cookies
            sessdata = client_cookies.get("SESSDATA") or resp.cookies.get("SESSDATA")
            bili_jct = client_cookies.get("bili_jct") or resp.cookies.get("bili_jct")
            buvid3 = client_cookies.get("buvid3") or resp.cookies.get("buvid3") or self.auth.buvid3

        if state_code == 86038 and QR_SESSION_FILE.exists():
            QR_SESSION_FILE.unlink(missing_ok=True)

        if state_code == 0:
            self.auth.sessdata = sessdata or self.auth.sessdata
            self.auth.bili_jct = bili_jct or self.auth.bili_jct
            self.auth.buvid3 = buvid3 or self.auth.buvid3
            if persist is not None:
                self.auth.persist = persist
            elif self.auth.persist and self.auth.is_authenticated:
                self.auth.save_to_file()
            verify = await self.auth.verify()
            QR_SESSION_FILE.unlink(missing_ok=True)
            return {
                "success": True,
                "schema": "bilibili.auth_client.poll_qr_login.v1",
                "status": status,
                "state_code": state_code,
                "message": payload.get("message") or default_message,
                "persisted": bool(self.auth.persist),
                "auth": {
                    "is_authenticated": self.auth.is_authenticated,
                    "credential_path": self.auth.credential_path,
                },
                "verify": verify,
            }

        return {
            "success": True,
            "schema": "bilibili.auth_client.poll_qr_login.v1",
            "status": status,
            "state_code": state_code,
            "message": payload.get("message") or default_message,
            "auth": {
                "is_authenticated": self.auth.is_authenticated,
                "credential_path": self.auth.credential_path,
            },
        }

    async def verify_auth(self) -> Dict[str, Any]:
        verify = await self.auth.verify()
        return {
            "success": verify.get("success", False),
            "schema": "bilibili.auth_client.verify_auth.v1",
            "auth": {
                "is_authenticated": self.auth.is_authenticated,
                "has_sessdata": bool(self.auth.sessdata),
                "has_bili_jct": bool(self.auth.bili_jct),
                "has_buvid3": bool(self.auth.buvid3),
                "persist": self.auth.persist,
                "credential_path": self.auth.credential_path,
            },
            "verify": verify,
            "message": verify.get("message", "Auth status checked"),
        }

    async def describe_auth(self) -> Dict[str, Any]:
        return {
            "success": True,
            "schema": "bilibili.auth_client.describe_auth.v1",
            "auth": {
                "is_authenticated": self.auth.is_authenticated,
                "has_sessdata": bool(self.auth.sessdata),
                "has_bili_jct": bool(self.auth.bili_jct),
                "has_buvid3": bool(self.auth.buvid3),
                "persist": self.auth.persist,
                "credential_path": self.auth.credential_path,
                "qr_session_file": str(QR_SESSION_FILE),
                "qr_image_path": str(QR_IMAGE_FILE),
                "qr_html_path": str(QR_HTML_FILE),
            },
            "preferred_login": "qr_login",
            "guidance": "Prefer QR login by default. Send/show the QR image first; only fall back to HTML or raw URL when the current session cannot display images.",
        }

    async def clear_auth(self, clear_persisted: bool = True, clear_runtime: bool = True) -> Dict[str, Any]:
        self.auth.sessdata = ""
        self.auth.bili_jct = ""
        self.auth.buvid3 = ""
        if clear_persisted:
            self.auth.clear_persisted()
        if clear_runtime:
            for path in (QR_SESSION_FILE, QR_IMAGE_FILE, QR_HTML_FILE):
                path.unlink(missing_ok=True)
        return {
            "success": True,
            "schema": "bilibili.auth_client.clear_auth.v1",
            "message": "Auth state cleared",
            "cleared": {
                "persisted": clear_persisted,
                "runtime": clear_runtime,
            },
        }

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "start_qr_login": self.start_qr_login,
            "poll_qr_login": self.poll_qr_login,
            "verify_auth": self.verify_auth,
            "describe_auth": self.describe_auth,
            "clear_auth": self.clear_auth,
        }
        handler = actions.get(action)
        if not handler:
            return {
                "success": False,
                "stage": "dispatch",
                "error_type": "unknown_action",
                "message": f"Unknown auth_client action: {action}",
            }
        return await handler(**kwargs)
