"""Live orchestration layer for Bilibili + OBS.

Design goals:
- keep sensitive RTMP server/key masked by default
- treat OBS as the stream transport authority
- handle real-world cleanup quirks (StopStream may require StopOutput fallback)
- expose preflight / start / stop / health-check flows for higher layers
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from .auth import BilibiliAuth
from .client_base import BILIBILI_API_AVAILABLE, BILIBILI_API_IMPORT_ERROR
from .obs_client import BilibiliOBSClient

try:
    from bilibili_api import Credential
    from bilibili_api import live as bili_live
    from bilibili_api import user as bili_user
except Exception:  # pragma: no cover - import guard
    Credential = None
    bili_live = None
    bili_user = None


class BilibiliLiveOrchestrator:
    """Minimal end-to-end live orchestration for Bilibili + OBS."""

    def __init__(self, auth: Optional[BilibiliAuth] = None):
        self.auth = auth or BilibiliAuth()
        self.obs = BilibiliOBSClient()

    @staticmethod
    def _success(**kwargs) -> Dict[str, Any]:
        return {"success": True, **kwargs}

    @staticmethod
    def _failure(message: str, **kwargs) -> Dict[str, Any]:
        return {"success": False, "message": message, **kwargs}

    @staticmethod
    def _mask_value(value: Optional[str], keep_start: int = 10, keep_end: int = 6) -> Optional[str]:
        if not value:
            return value
        value = str(value)
        if len(value) <= keep_start + keep_end:
            return "*" * len(value)
        return value[:keep_start] + ("*" * (len(value) - keep_start - keep_end)) + value[-keep_end:]

    def _require_library(self) -> Optional[Dict[str, Any]]:
        if BILIBILI_API_AVAILABLE and Credential and bili_live and bili_user:
            return None
        return self._failure(
            "bilibili_api library is required for live orchestration.",
            detail=BILIBILI_API_IMPORT_ERROR,
        )

    def _require_auth(self) -> Optional[Dict[str, Any]]:
        if self.auth and self.auth.is_authenticated:
            return None
        return self._failure("Authenticated Bilibili cookies are required for live orchestration.")

    def _credential(self):
        return Credential(
            sessdata=self.auth.sessdata or "",
            bili_jct=self.auth.bili_jct or "",
            buvid3=self.auth.buvid3 or "",
        )

    async def _get_self_uid(self) -> int:
        profile = await bili_user.get_self_info(self._credential())
        return int(profile["mid"])

    async def _get_live_room_bundle(self, uid: Optional[int] = None) -> Dict[str, Any]:
        uid = int(uid or await self._get_self_uid())
        async with self.auth.get_client() as client:
            resp = await client.get(f"https://api.live.bilibili.com/live_user/v1/Master/info?uid={uid}")
            data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(data.get("message", "Failed to fetch live room info"))
        room = data.get("data") or {}
        room_id = room.get("room_id")
        if not room_id:
            raise RuntimeError("Live room id not found for current account")
        return {
            "uid": uid,
            "room_id": int(room_id),
            "raw": room,
        }

    async def _get_current_area(self, room_id: int) -> Optional[Dict[str, Any]]:
        async with self.auth.get_client() as client:
            resp = await client.get(f"https://api.live.bilibili.com/room/v1/Area/getMyChooseArea?roomid={int(room_id)}")
            data = resp.json()
        if data.get("code") != 0:
            return None
        items = data.get("data") or []
        if not items:
            return None
        item = items[0] or {}
        return {
            "id": int(item.get("id")) if item.get("id") is not None else None,
            "name": item.get("name"),
            "parent_id": int(item.get("parent_id")) if item.get("parent_id") is not None else None,
            "parent_name": item.get("parent_name"),
            "raw": item,
        }

    async def _room(self, room_id: int):
        return bili_live.LiveRoom(int(room_id), credential=self._credential())

    async def _get_room_info(self, room_id: int) -> Dict[str, Any]:
        async with self.auth.get_client() as client:
            resp = await client.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={int(room_id)}")
            data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(data.get("message", "Failed to fetch room info"))
        return data.get("data") or {}

    async def _get_stop_live_data(self, live_key: str) -> Dict[str, Any]:
        async with self.auth.get_client() as client:
            resp = await client.get(
                f"https://api.live.bilibili.com/xlive/app-blink/v1/live/StopLiveData?live_key={live_key}"
            )
            data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(data.get("message", "Failed to fetch stop-live stats"))
        payload = data.get("data") or {}
        return {
            "live_key": self._mask_value(live_key, 8, 6),
            "summary": {
                "live_time": payload.get("LiveTime"),
                "add_fans": payload.get("AddFans"),
                "hamster_rmb": payload.get("HamsterRmb"),
                "new_fans_club": payload.get("NewFansClub"),
                "danmu_num": payload.get("DanmuNum"),
                "max_online": payload.get("MaxOnline"),
                "watched_count": payload.get("WatchedCount"),
            },
            "raw": payload,
        }

    async def get_live_room_profile(
        self,
        room_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if (err := self._require_library()) or (err := self._require_auth()):
            return err
        try:
            bundle = await self._get_live_room_bundle()
            resolved_room_id = int(room_id or bundle["room_id"])
            room_info = await self._get_room_info(resolved_room_id)
            current_area = await self._get_current_area(resolved_room_id)
            return self._success(
                schema="bilibili.live_orchestrator.get_live_room_profile.v1",
                room_id=resolved_room_id,
                uid=bundle["uid"],
                title=room_info.get("title"),
                description=room_info.get("description"),
                live_status=room_info.get("live_status"),
                area=current_area,
                room_news=(bundle.get("raw") or {}).get("room_news"),
                room_info=room_info,
            )
        except Exception as exc:
            return self._failure(f"Failed to fetch live room profile: {exc}")

    async def update_live_announcement(
        self,
        content: str,
        room_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if (err := self._require_library()) or (err := self._require_auth()):
            return err
        if not content:
            return self._failure("content is required")
        try:
            bundle = await self._get_live_room_bundle()
            resolved_room_id = int(room_id or bundle["room_id"])
            room = await self._room(resolved_room_id)
            result = await room.update_news(content)
            return self._success(
                schema="bilibili.live_orchestrator.update_live_announcement.v1",
                room_id=resolved_room_id,
                content=content,
                result=result,
            )
        except Exception as exc:
            return self._failure(f"Failed to update live announcement: {exc}")

    async def prepare_live_session(
        self,
        room_id: Optional[int] = None,
        area_id: Optional[int] = None,
        obs_host: Optional[str] = None,
        obs_port: Optional[int] = None,
        obs_password: Optional[str] = None,
        obs_timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        if (err := self._require_library()) or (err := self._require_auth()):
            return err
        try:
            bundle = await self._get_live_room_bundle()
            resolved_room_id = int(room_id or bundle["room_id"])
            current_area = await self._get_current_area(resolved_room_id)
            resolved_area_id = int(area_id or (current_area or {}).get("id") or 0)
            obs_connection = await self.obs.connect_test(
                host=obs_host,
                port=obs_port,
                password=obs_password,
                timeout=obs_timeout,
            )
            obs_status = await self.obs.get_status(
                host=obs_host,
                port=obs_port,
                password=obs_password,
                timeout=obs_timeout,
            )
            obs_stream_service = await self.obs.get_stream_service(
                host=obs_host,
                port=obs_port,
                password=obs_password,
                timeout=obs_timeout,
            )
            room_info = await self._get_room_info(resolved_room_id)
            return self._success(
                schema="bilibili.live_orchestrator.prepare_live_session.v1",
                room_id=resolved_room_id,
                area_id=resolved_area_id or None,
                uid=bundle["uid"],
                current_area=current_area,
                room_profile={
                    "title": room_info.get("title"),
                    "description": room_info.get("description"),
                    "area_id": room_info.get("area_id"),
                    "area_name": room_info.get("area_name"),
                    "parent_area_id": room_info.get("parent_area_id"),
                    "parent_area_name": room_info.get("parent_area_name"),
                    "live_status": room_info.get("live_status"),
                    "room_news": (bundle.get("raw") or {}).get("room_news"),
                },
                obs_connection=obs_connection,
                obs_status=obs_status,
                obs_stream_service=obs_stream_service,
            )
        except Exception as exc:
            return self._failure(f"Failed to prepare live session: {exc}")

    async def start_live_session(
        self,
        room_id: Optional[int] = None,
        area_id: Optional[int] = None,
        obs_host: Optional[str] = None,
        obs_port: Optional[int] = None,
        obs_password: Optional[str] = None,
        obs_timeout: Optional[float] = None,
        reveal_sensitive: bool = False,
        auto_start_obs: bool = True,
        settle_seconds: float = 2.0,
    ) -> Dict[str, Any]:
        if (err := self._require_library()) or (err := self._require_auth()):
            return err
        try:
            bundle = await self._get_live_room_bundle()
            resolved_room_id = int(room_id or bundle["room_id"])
            current_area = await self._get_current_area(resolved_room_id)
            resolved_area_id = int(area_id or (current_area or {}).get("id") or 0)
            if not resolved_area_id:
                return self._failure("No live area_id available. Provide area_id explicitly or choose an area in Bilibili first.")

            original_service = await self.obs.get_stream_service(
                host=obs_host,
                port=obs_port,
                password=obs_password,
                timeout=obs_timeout,
                reveal_sensitive=True,
            )
            room = await self._room(resolved_room_id)
            start_resp = await room.start(resolved_area_id)
            rtmp = start_resp.get("rtmp") or {}
            server = rtmp.get("addr")
            key = rtmp.get("code")
            need_face_auth = bool(start_resp.get("need_face_auth"))
            qr = start_resp.get("qr")
            if need_face_auth or qr:
                return self._failure(
                    "Live start requires operator verification.",
                    schema="bilibili.live_orchestrator.start_live_session.v1",
                    room_id=resolved_room_id,
                    area_id=resolved_area_id,
                    operator_action_required=True,
                    verification={
                        "need_face_auth": need_face_auth,
                        "qr": qr,
                    },
                    cleanup_hint="If the room entered a partial live state, run stop_live_session after verification or cancel manually.",
                )
            if not server or not key:
                return self._failure(
                    "Live start returned no RTMP server/key.",
                    schema="bilibili.live_orchestrator.start_live_session.v1",
                    room_id=resolved_room_id,
                    area_id=resolved_area_id,
                    start_response_keys=list(start_resp.keys()),
                )

            apply_resp = await self.obs.set_stream_service(
                server=server,
                key=key,
                service_type="rtmp_custom",
                reveal_sensitive=reveal_sensitive,
                host=obs_host,
                port=obs_port,
                password=obs_password,
                timeout=obs_timeout,
                use_auth=False,
                bwtest=False,
            )
            obs_start = None
            if auto_start_obs:
                obs_start = await self.obs.start_stream(
                    host=obs_host,
                    port=obs_port,
                    password=obs_password,
                    timeout=obs_timeout,
                )
                await asyncio.sleep(max(0.0, float(settle_seconds)))
            obs_status = await self.obs.get_status(
                host=obs_host,
                port=obs_port,
                password=obs_password,
                timeout=obs_timeout,
            )
            return self._success(
                schema="bilibili.live_orchestrator.start_live_session.v1",
                room_id=resolved_room_id,
                area_id=resolved_area_id,
                bilibili={
                    "started": True,
                    "status": start_resp.get("status"),
                    "change": start_resp.get("change"),
                    "live_key": start_resp.get("live_key") if reveal_sensitive else self._mask_value(start_resp.get("live_key"), 8, 6),
                    "rtmp": {
                        "addr": server if reveal_sensitive else self._mask_value(server, 22, 8),
                        "code": key if reveal_sensitive else self._mask_value(key, 12, 8),
                    },
                },
                obs_apply=apply_resp,
                obs_start=obs_start,
                obs_status=obs_status,
                previous_obs_stream_service=original_service,
            )
        except Exception as exc:
            return self._failure(f"Failed to start live session: {exc}")

    async def stop_live_session(
        self,
        room_id: Optional[int] = None,
        live_key: Optional[str] = None,
        obs_host: Optional[str] = None,
        obs_port: Optional[int] = None,
        obs_password: Optional[str] = None,
        obs_timeout: Optional[float] = None,
        restore_stream_service: bool = False,
        restore_service_type: Optional[str] = None,
        restore_server: Optional[str] = None,
        restore_key: Optional[str] = None,
        reveal_sensitive: bool = False,
    ) -> Dict[str, Any]:
        if (err := self._require_library()) or (err := self._require_auth()):
            return err
        try:
            bundle = await self._get_live_room_bundle()
            resolved_room_id = int(room_id or bundle["room_id"])
            obs_stop = await self.obs.stop_stream(
                host=obs_host,
                port=obs_port,
                password=obs_password,
                timeout=obs_timeout,
            )
            room = await self._room(resolved_room_id)
            stop_resp = await room.stop()
            stop_stats = None
            if live_key:
                try:
                    stop_stats = await self._get_stop_live_data(live_key)
                except Exception as exc:
                    stop_stats = {"success": False, "message": str(exc), "live_key": self._mask_value(live_key, 8, 6)}
            restore_resp = None
            if restore_stream_service and restore_server and restore_key:
                restore_resp = await self.obs.set_stream_service(
                    server=restore_server,
                    key=restore_key,
                    service_type=restore_service_type or "rtmp_custom",
                    reveal_sensitive=reveal_sensitive,
                    host=obs_host,
                    port=obs_port,
                    password=obs_password,
                    timeout=obs_timeout,
                )
            obs_status = await self.obs.get_status(
                host=obs_host,
                port=obs_port,
                password=obs_password,
                timeout=obs_timeout,
            )
            return self._success(
                schema="bilibili.live_orchestrator.stop_live_session.v2",
                room_id=resolved_room_id,
                obs_stop=obs_stop,
                bilibili_stop={
                    "status": stop_resp.get("status"),
                    "change": stop_resp.get("change"),
                    "raw": stop_resp,
                },
                stop_stats=stop_stats,
                obs_restore=restore_resp,
                obs_status=obs_status,
            )
        except Exception as exc:
            return self._failure(f"Failed to stop live session: {exc}")

    async def live_health_check(
        self,
        room_id: Optional[int] = None,
        obs_host: Optional[str] = None,
        obs_port: Optional[int] = None,
        obs_password: Optional[str] = None,
        obs_timeout: Optional[float] = None,
        transient_grace_seconds: float = 8.0,
    ) -> Dict[str, Any]:
        if (err := self._require_library()) or (err := self._require_auth()):
            return err
        try:
            bundle = await self._get_live_room_bundle()
            resolved_room_id = int(room_id or bundle["room_id"])
            room = await self._room(resolved_room_id)
            room_play = await room.get_room_play_info()
            room_info = await self._get_room_info(resolved_room_id)
            obs_status = await self.obs.get_status(
                host=obs_host,
                port=obs_port,
                password=obs_password,
                timeout=obs_timeout,
            )
            bilibili_live_status = (room_play or {}).get("live_status")
            bilibili_live_time = (room_play or {}).get("live_time")
            obs_active = ((obs_status or {}).get("stream") or {}).get("active")
            obs_reconnecting = ((obs_status or {}).get("stream") or {}).get("reconnecting")
            obs_duration_ms = ((obs_status or {}).get("stream") or {}).get("duration_ms") or 0
            state = "healthy"
            transitional = False
            reasons = []
            if bilibili_live_status == 0 and obs_active and obs_duration_ms <= max(0, int(transient_grace_seconds * 1000)):
                state = "transient_stop_settling"
                transitional = True
                reasons.append("OBS still draining shortly after stop while Bilibili already reports offline")
            elif bool(bilibili_live_status) != bool(obs_active):
                state = "split_state"
                reasons.append("Bilibili live_status and OBS output_active disagree")
            elif obs_reconnecting:
                state = "obs_reconnecting"
                reasons.append("OBS output is reconnecting")
            return self._success(
                schema="bilibili.live_orchestrator.live_health_check.v2",
                room_id=resolved_room_id,
                bilibili={
                    "live_status": bilibili_live_status,
                    "live_time": bilibili_live_time,
                    "room_play_info": room_play,
                    "room_info": room_info,
                },
                obs_status=obs_status,
                state=state,
                transitional=transitional,
                reasons=reasons,
            )
        except Exception as exc:
            return self._failure(f"Failed to run live health check: {exc}")

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "get_live_room_profile": self.get_live_room_profile,
            "room_profile": self.get_live_room_profile,
            "update_live_announcement": self.update_live_announcement,
            "set_announcement": self.update_live_announcement,
            "prepare_live_session": self.prepare_live_session,
            "start_live_session": self.start_live_session,
            "stop_live_session": self.stop_live_session,
            "live_health_check": self.live_health_check,
            "health_check": self.live_health_check,
        }
        handler = actions.get(action)
        if not handler:
            return self._failure(f"Unknown live_orchestrator action: {action}")
        try:
            return await handler(**kwargs)
        except TypeError as exc:
            return self._failure(f"Invalid parameters for live_orchestrator.{action}: {exc}")
