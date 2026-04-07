"""OBS websocket control for live orchestration.

Default posture:
- connect to OBS directly for start/stop/status control
- do not reveal full stream server/key unless explicitly requested
- keep this module focused on transport/control; Bilibili live orchestration can sit above it
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


try:
    from obsws_python import ReqClient
    OBSWS_AVAILABLE = True
    OBSWS_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - import guard
    ReqClient = None
    OBSWS_AVAILABLE = False
    OBSWS_IMPORT_ERROR = str(exc)


class BilibiliOBSClient:
    """Thin OBS websocket control layer for live orchestration."""

    def __init__(self):
        self.default_host = os.getenv("OBS_WEBSOCKET_HOST", "127.0.0.1")
        self.default_port = int(os.getenv("OBS_WEBSOCKET_PORT", "4455"))
        self.default_password = os.getenv("OBS_WEBSOCKET_PASSWORD", "")
        self.default_timeout = float(os.getenv("OBS_WEBSOCKET_TIMEOUT", "5"))

    @staticmethod
    def _success(**kwargs) -> Dict[str, Any]:
        return {"success": True, **kwargs}

    @staticmethod
    def _failure(message: str, **kwargs) -> Dict[str, Any]:
        return {"success": False, "message": message, **kwargs}

    def _require_library(self) -> Optional[Dict[str, Any]]:
        if OBSWS_AVAILABLE:
            return None
        return self._failure(
            "obsws-python is required for OBS websocket control.",
            detail=OBSWS_IMPORT_ERROR,
        )

    @staticmethod
    def _mask_value(value: Optional[str], keep_start: int = 8, keep_end: int = 4) -> Optional[str]:
        if not value:
            return value
        if len(value) <= keep_start + keep_end:
            return "*" * len(value)
        return f"{value[:keep_start]}{'*' * (len(value) - keep_start - keep_end)}{value[-keep_end:]}"

    def _resolve_conn(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        resolved_password = self.default_password if password is None else password
        return {
            "host": host or self.default_host,
            "port": int(port or self.default_port),
            "password": resolved_password,
            "timeout": float(timeout or self.default_timeout),
        }

    def _client(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        lib_error = self._require_library()
        if lib_error:
            raise RuntimeError(lib_error["message"])
        conn = self._resolve_conn(host=host, port=port, password=password, timeout=timeout)
        return ReqClient(
            host=conn["host"],
            port=conn["port"],
            password=conn["password"],
            timeout=conn["timeout"],
        )

    def _safe_stream_settings(self, data: Dict[str, Any], reveal_sensitive: bool = False) -> Dict[str, Any]:
        settings = dict(data or {})
        if not reveal_sensitive:
            if "server" in settings:
                settings["server"] = self._mask_value(settings.get("server"), keep_start=18, keep_end=8)
            if "key" in settings:
                settings["key"] = self._mask_value(settings.get("key"), keep_start=10, keep_end=6)
        return settings

    async def connect_test(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        try:
            client = self._client(host=host, port=port, password=password, timeout=timeout)
            version = client.get_version()
            return self._success(
                host=host or self.default_host,
                port=int(port or self.default_port),
                connected=True,
                obs_version=getattr(version, "obs_version", None),
                obs_websocket_version=getattr(version, "obs_web_socket_version", None),
                rpc_version=getattr(version, "rpc_version", None),
                platform=getattr(version, "platform", None),
            )
        except Exception as exc:
            return self._failure(f"Failed to connect to OBS websocket: {exc}")

    async def get_status(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        try:
            client = self._client(host=host, port=port, password=password, timeout=timeout)
            stream = client.get_stream_status()
            record = client.get_record_status()
            stats = client.get_stats()
            scene = client.get_current_program_scene()
            return self._success(
                schema="bilibili.obs_client.status.v1",
                stream={
                    "active": getattr(stream, "output_active", None),
                    "reconnecting": getattr(stream, "output_reconnecting", None),
                    "duration_ms": getattr(stream, "output_duration", None),
                    "bytes": getattr(stream, "output_bytes", None),
                    "skipped_frames": getattr(stream, "output_skipped_frames", None),
                    "total_frames": getattr(stream, "output_total_frames", None),
                    "congestion": getattr(stream, "output_congestion", None),
                    "timecode": getattr(stream, "output_timecode", None),
                },
                record={
                    "active": getattr(record, "output_active", None),
                    "paused": getattr(record, "output_paused", None),
                    "duration_ms": getattr(record, "output_duration", None),
                    "bytes": getattr(record, "output_bytes", None),
                    "timecode": getattr(record, "output_timecode", None),
                },
                stats={
                    "active_fps": getattr(stats, "active_fps", None),
                    "cpu_usage": getattr(stats, "cpu_usage", None),
                    "memory_usage": getattr(stats, "memory_usage", None),
                    "available_disk_space": getattr(stats, "available_disk_space", None),
                    "render_skipped_frames": getattr(stats, "render_skipped_frames", None),
                    "render_total_frames": getattr(stats, "render_total_frames", None),
                    "output_skipped_frames": getattr(stats, "output_skipped_frames", None),
                    "output_total_frames": getattr(stats, "output_total_frames", None),
                },
                current_program_scene={
                    "name": getattr(scene, "current_program_scene_name", None),
                    "uuid": getattr(scene, "current_program_scene_uuid", None),
                },
            )
        except Exception as exc:
            return self._failure(f"Failed to fetch OBS status: {exc}")

    async def get_stream_service(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
        reveal_sensitive: bool = False,
    ) -> Dict[str, Any]:
        try:
            client = self._client(host=host, port=port, password=password, timeout=timeout)
            service = client.get_stream_service_settings()
            settings = getattr(service, "stream_service_settings", {}) or {}
            return self._success(
                schema="bilibili.obs_client.stream_service.v1",
                stream_service_type=getattr(service, "stream_service_type", None),
                stream_service_settings=self._safe_stream_settings(settings, reveal_sensitive=reveal_sensitive),
                has_server=bool(settings.get("server")),
                has_key=bool(settings.get("key")),
                reveal_sensitive=bool(reveal_sensitive),
            )
        except Exception as exc:
            return self._failure(f"Failed to fetch OBS stream service settings: {exc}")

    async def set_stream_service(
        self,
        server: str,
        key: str,
        service_type: str = "rtmp_custom",
        reveal_sensitive: bool = False,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
        **extra_settings,
    ) -> Dict[str, Any]:
        if not server:
            return self._failure("server is required")
        if not key:
            return self._failure("key is required")
        try:
            client = self._client(host=host, port=port, password=password, timeout=timeout)
            settings = {"server": server, "key": key, **extra_settings}
            client.set_stream_service_settings(service_type, settings)
            return self._success(
                schema="bilibili.obs_client.set_stream_service.v1",
                applied=True,
                stream_service_type=service_type,
                stream_service_settings=self._safe_stream_settings(settings, reveal_sensitive=reveal_sensitive),
                reveal_sensitive=bool(reveal_sensitive),
            )
        except Exception as exc:
            return self._failure(f"Failed to update OBS stream service settings: {exc}")

    async def start_stream(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        try:
            client = self._client(host=host, port=port, password=password, timeout=timeout)
            client.start_stream()
            status = client.get_stream_status()
            return self._success(
                schema="bilibili.obs_client.start_stream.v1",
                started=True,
                output_active=getattr(status, "output_active", None),
                output_reconnecting=getattr(status, "output_reconnecting", None),
            )
        except Exception as exc:
            return self._failure(f"Failed to start OBS stream: {exc}")

    async def stop_stream(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        try:
            client = self._client(host=host, port=port, password=password, timeout=timeout)
            client.stop_stream()
            status = client.get_stream_status()
            return self._success(
                schema="bilibili.obs_client.stop_stream.v1",
                stopped=True,
                output_active=getattr(status, "output_active", None),
                output_reconnecting=getattr(status, "output_reconnecting", None),
            )
        except Exception as exc:
            return self._failure(f"Failed to stop OBS stream: {exc}")

    async def get_current_program_scene(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        try:
            client = self._client(host=host, port=port, password=password, timeout=timeout)
            scene = client.get_current_program_scene()
            return self._success(
                schema="bilibili.obs_client.current_scene.v1",
                current_program_scene_name=getattr(scene, "current_program_scene_name", None),
                current_program_scene_uuid=getattr(scene, "current_program_scene_uuid", None),
            )
        except Exception as exc:
            return self._failure(f"Failed to fetch OBS current scene: {exc}")

    async def handle(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "connect_test": self.connect_test,
            "verify_connection": self.connect_test,
            "get_status": self.get_status,
            "status": self.get_status,
            "get_stream_service": self.get_stream_service,
            "stream_service": self.get_stream_service,
            "set_stream_service": self.set_stream_service,
            "apply_stream_target": self.set_stream_service,
            "start_stream": self.start_stream,
            "stop_stream": self.stop_stream,
            "get_current_program_scene": self.get_current_program_scene,
            "current_scene": self.get_current_program_scene,
        }
        if action not in actions:
            return self._failure(f"Unknown obs_client action: {action}")
        try:
            return await actions[action](**kwargs)
        except TypeError as exc:
            return self._failure(f"Invalid parameters for obs_client.{action}: {exc}")
        except Exception as exc:
            return self._failure(str(exc))

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        return await self.handle(action=action, **kwargs)
