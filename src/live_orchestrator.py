"""Live orchestration layer for Bilibili + OBS.

Design goals:
- keep sensitive RTMP server/key masked by default
- treat OBS as the stream transport authority
- handle real-world cleanup quirks (StopStream may require StopOutput fallback)
- expose preflight / start / stop / health-check flows for higher layers
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .auth import BilibiliAuth
from .client_base import BILIBILI_API_AVAILABLE, BILIBILI_API_IMPORT_ERROR
from .obs_client import BilibiliOBSClient
from .workspace_paths import workspace_path

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
        self.session_cache_path = workspace_path("bilibili-live-session.json")
        self.runtime_log_path = workspace_path("bilibili-live-runtime.jsonl")

    def _read_session_cache(self) -> Optional[Dict[str, Any]]:
        try:
            if not self.session_cache_path.exists():
                return None
            data = json.loads(self.session_cache_path.read_text())
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _write_session_cache(self, payload: Dict[str, Any]) -> None:
        self.session_cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    def _update_session_cache(self, **patch: Any) -> Dict[str, Any]:
        current = self._read_session_cache() or {
            "schema": "bilibili.live_orchestrator.session_cache.v1",
        }
        current.update(patch)
        current["updated_at"] = int(time.time())
        self._write_session_cache(current)
        return current

    def _present_session_cache(self, cache: Optional[Dict[str, Any]], reveal_sensitive: bool = False) -> Optional[Dict[str, Any]]:
        if not isinstance(cache, dict):
            return None
        presented = json.loads(json.dumps(cache))
        if reveal_sensitive:
            return presented
        if presented.get("live_key"):
            presented["live_key"] = self._mask_value(presented.get("live_key"), 8, 6)
        if presented.get("last_live_key"):
            presented["last_live_key"] = self._mask_value(presented.get("last_live_key"), 8, 6)
        restore_stream_service = presented.get("restore_stream_service")
        if isinstance(restore_stream_service, dict):
            stream_service = restore_stream_service.get("stream_service") or {}
            settings = stream_service.get("settings") or {}
            if settings.get("server"):
                settings["server"] = self._mask_value(settings.get("server"), 22, 8)
            if settings.get("key"):
                settings["key"] = self._mask_value(settings.get("key"), 12, 8)
        bilibili_start_response = presented.get("bilibili_start_response")
        if isinstance(bilibili_start_response, dict):
            rtmp = bilibili_start_response.get("rtmp") or {}
            if bilibili_start_response.get("live_key"):
                bilibili_start_response["live_key"] = self._mask_value(bilibili_start_response.get("live_key"), 8, 6)
            if rtmp.get("addr"):
                rtmp["addr"] = self._mask_value(rtmp.get("addr"), 22, 8)
            if rtmp.get("code"):
                rtmp["code"] = self._mask_value(rtmp.get("code"), 12, 8)
        return presented

    async def get_live_session_cache(self, reveal_sensitive: bool = False) -> Dict[str, Any]:
        cache = self._read_session_cache()
        return self._success(
            schema="bilibili.live_orchestrator.get_live_session_cache.v1",
            path=str(self.session_cache_path),
            exists=self.session_cache_path.exists(),
            active=bool((cache or {}).get("active")),
            room_id=(cache or {}).get("room_id"),
            area_id=(cache or {}).get("area_id"),
            has_live_key=bool((cache or {}).get("live_key")),
            has_last_live_key=bool((cache or {}).get("last_live_key")),
            reveal_sensitive=reveal_sensitive,
            cache=self._present_session_cache(cache, reveal_sensitive=reveal_sensitive),
        )

    async def clear_live_session_cache(self) -> Dict[str, Any]:
        cache = self._read_session_cache()
        existed = self.session_cache_path.exists()
        if existed:
            self.session_cache_path.unlink()
        return self._success(
            schema="bilibili.live_orchestrator.clear_live_session_cache.v1",
            path=str(self.session_cache_path),
            existed=existed,
            cleared=True,
            previous_active=bool((cache or {}).get("active")),
            previous_room_id=(cache or {}).get("room_id"),
            had_live_key=bool((cache or {}).get("live_key")),
        )


    def _append_runtime_log(self, entry: Dict[str, Any]) -> None:
        self.runtime_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.runtime_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _read_runtime_log(self, limit: int = 20) -> list[Dict[str, Any]]:
        if not self.runtime_log_path.exists():
            return []
        lines = self.runtime_log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        items = []
        for line in lines[-max(0, int(limit)):]:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                items.append(obj)
        return items

    async def get_live_runtime_log(self, limit: int = 20) -> Dict[str, Any]:
        entries = self._read_runtime_log(limit=limit)
        return self._success(
            schema="bilibili.live_orchestrator.get_live_runtime_log.v1",
            path=str(self.runtime_log_path),
            exists=self.runtime_log_path.exists(),
            count=len(entries),
            entries=entries,
        )

    async def clear_live_runtime_log(self) -> Dict[str, Any]:
        existed = self.runtime_log_path.exists()
        previous_count = len(self._read_runtime_log(limit=100000)) if existed else 0
        if existed:
            self.runtime_log_path.unlink()
        return self._success(
            schema="bilibili.live_orchestrator.clear_live_runtime_log.v1",
            path=str(self.runtime_log_path),
            existed=existed,
            cleared=True,
            previous_count=previous_count,
        )

    async def get_live_runtime_stats(
        self,
        room_id: Optional[int] = None,
        live_key: Optional[str] = None,
        use_session_cache: bool = True,
        include_overview: bool = True,
        reveal_sensitive: bool = False,
    ) -> Dict[str, Any]:
        if (err := self._require_library()) or (err := self._require_auth()):
            return err
        try:
            bundle = await self._get_live_room_bundle()
            cache = self._read_session_cache() if use_session_cache else None
            resolved_room_id = int(room_id or (cache or {}).get("room_id") or bundle["room_id"])
            resolved_live_key = live_key or (cache or {}).get("live_key") or (cache or {}).get("last_live_key")
            room = await self._room(resolved_room_id)
            room_play = await room.get_room_play_info()
            room_info = await self._get_room_info(resolved_room_id)
            stop_like_stats = None
            stop_like_stats_error = None
            if resolved_live_key:
                try:
                    stop_like_stats = await self._get_stop_live_data(resolved_live_key)
                    if not reveal_sensitive and isinstance(stop_like_stats, dict):
                        stop_like_stats["live_key"] = self._mask_value(resolved_live_key, 8, 6)
                    elif isinstance(stop_like_stats, dict):
                        stop_like_stats["live_key"] = resolved_live_key
                except Exception as exc:
                    stop_like_stats_error = str(exc)
            overview = None
            overview_error = None
            if include_overview:
                try:
                    overview = await self._get_live_overview()
                except Exception as exc:
                    overview_error = str(exc)
            live_status = (room_play or {}).get("live_status")
            is_live = bool(live_status)
            return self._success(
                schema="bilibili.live_orchestrator.get_live_runtime_stats.v1",
                room_id=resolved_room_id,
                live_key=resolved_live_key if reveal_sensitive else self._mask_value(resolved_live_key, 8, 6),
                used_cached_live_key=bool(use_session_cache and not live_key and ((cache or {}).get("live_key") or (cache or {}).get("last_live_key"))),
                provisional=bool(is_live),
                note="Live-session stats fetched mid-stream are provisional and may continue changing until stop." if is_live else None,
                room_play_info=room_play,
                room_info=room_info,
                stop_like_stats=stop_like_stats,
                stop_like_stats_error=stop_like_stats_error,
                overview=overview,
                overview_error=overview_error,
            )
        except Exception as exc:
            return self._failure(f"Failed to fetch live runtime stats: {exc}")

    async def watch_live_runtime(
        self,
        room_id: Optional[int] = None,
        live_key: Optional[str] = None,
        use_session_cache: bool = True,
        include_overview: bool = True,
        interval_seconds: float = 10.0,
        samples: int = 6,
        clear_log_first: bool = False,
        reveal_sensitive: bool = False,
    ) -> Dict[str, Any]:
        if (err := self._require_library()) or (err := self._require_auth()):
            return err
        try:
            if clear_log_first and self.runtime_log_path.exists():
                self.runtime_log_path.unlink()
            interval_seconds = max(1.0, float(interval_seconds))
            samples = max(1, int(samples))
            collected = []
            for idx in range(samples):
                stats = await self.get_live_runtime_stats(
                    room_id=room_id,
                    live_key=live_key,
                    use_session_cache=use_session_cache,
                    include_overview=include_overview,
                    reveal_sensitive=reveal_sensitive,
                )
                if not stats.get("success"):
                    return self._failure(
                        "Failed to watch live runtime because a sample fetch failed.",
                        schema="bilibili.live_orchestrator.watch_live_runtime.v1",
                        failed_sample_index=idx + 1,
                        sample_error=stats,
                    )
                entry = {
                    "schema": "bilibili.live_orchestrator.runtime_log_entry.v1",
                    "sample_index": idx + 1,
                    "captured_at": int(time.time()),
                    "room_id": stats.get("room_id"),
                    "live_key": stats.get("live_key"),
                    "provisional": stats.get("provisional"),
                    "room_play_info": stats.get("room_play_info"),
                    "room_info": stats.get("room_info"),
                    "stop_like_stats": stats.get("stop_like_stats"),
                    "overview": stats.get("overview"),
                }
                self._append_runtime_log(entry)
                collected.append(entry)
                if idx + 1 < samples:
                    await asyncio.sleep(interval_seconds)
            return self._success(
                schema="bilibili.live_orchestrator.watch_live_runtime.v1",
                path=str(self.runtime_log_path),
                samples_requested=samples,
                samples_collected=len(collected),
                interval_seconds=interval_seconds,
                latest=collected[-1] if collected else None,
            )
        except Exception as exc:
            return self._failure(f"Failed to watch live runtime: {exc}")

    async def recover_live_session(
        self,
        room_id: Optional[int] = None,
        live_key: Optional[str] = None,
        use_session_cache: bool = True,
        obs_host: Optional[str] = None,
        obs_port: Optional[int] = None,
        obs_password: Optional[str] = None,
        obs_timeout: Optional[float] = None,
        reveal_sensitive: bool = False,
        include_runtime_stats: bool = True,
        include_overview: bool = True,
        transient_grace_seconds: float = 8.0,
    ) -> Dict[str, Any]:
        if (err := self._require_library()) or (err := self._require_auth()):
            return err
        try:
            cache = self._read_session_cache() if use_session_cache else None
            health = await self.live_health_check(
                room_id=room_id or (cache or {}).get("room_id"),
                obs_host=obs_host,
                obs_port=obs_port,
                obs_password=obs_password,
                obs_timeout=obs_timeout,
                transient_grace_seconds=transient_grace_seconds,
            )
            if not health.get("success"):
                return self._failure(
                    "Failed to recover live session because health check failed.",
                    schema="bilibili.live_orchestrator.recover_live_session.v1",
                    health=health,
                )
            bilibili = health.get("bilibili") or {}
            obs_status = health.get("obs_status") or {}
            bilibili_live_status = bilibili.get("live_status")
            obs_stream = obs_status.get("stream") or {}
            obs_active = bool(obs_stream.get("active"))
            resolved_room_id = health.get("room_id")
            resolved_live_key = live_key or (cache or {}).get("live_key") or (cache or {}).get("last_live_key")
            runtime_stats = None
            if include_runtime_stats and resolved_live_key:
                runtime_stats = await self.get_live_runtime_stats(
                    room_id=resolved_room_id,
                    live_key=resolved_live_key,
                    use_session_cache=use_session_cache,
                    include_overview=include_overview,
                    reveal_sensitive=reveal_sensitive,
                )
            recommendation = "none"
            reasoning = []
            if bilibili_live_status or obs_active:
                recommendation = "stop_live_session"
                reasoning.append("At least one live component is still active.")
                if not resolved_live_key:
                    reasoning.append("A cached live_key is missing, so stop can still run but stop-session stats may be unavailable.")
            elif cache and cache.get("active"):
                recommendation = "clear_live_session_cache"
                reasoning.append("Live appears offline but cache still claims an active session.")
            elif cache and (cache.get("last_live_key") or cache.get("last_stop_stats")):
                recommendation = "inspect_or_clear_cache"
                reasoning.append("Live is offline; only historical cache residue remains.")
            recovery = {
                "recommended_action": recommendation,
                "reasoning": reasoning,
                "stop_command_ready": recommendation == "stop_live_session",
                "clear_cache_ready": recommendation in {"clear_live_session_cache", "inspect_or_clear_cache"},
                "has_live_key": bool(resolved_live_key),
                "used_session_cache": bool(cache) and use_session_cache,
            }
            return self._success(
                schema="bilibili.live_orchestrator.recover_live_session.v1",
                room_id=resolved_room_id,
                live_key=resolved_live_key if reveal_sensitive else self._mask_value(resolved_live_key, 8, 6),
                cache=self._present_session_cache(cache, reveal_sensitive=reveal_sensitive),
                health=health,
                runtime_stats=runtime_stats,
                recovery=recovery,
            )
        except Exception as exc:
            return self._failure(f"Failed to recover live session: {exc}")

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
        live_time = payload.get("LiveTime")
        add_fans = payload.get("AddFans")
        hamster_rmb = payload.get("HamsterRmb")
        new_fans_club = payload.get("NewFansClub")
        danmu_num = payload.get("DanmuNum")
        max_online = payload.get("MaxOnline")
        watched_count = payload.get("WatchedCount")
        duration_seconds = live_time if isinstance(live_time, int) and live_time >= 0 else None
        duration_minutes = round(duration_seconds / 60, 2) if duration_seconds is not None else None
        summary = {
            "duration_seconds": duration_seconds,
            "duration_minutes": duration_minutes,
            "watched_count": watched_count,
            "max_online": max_online,
            "danmu_num": danmu_num,
            "add_fans": add_fans,
            "new_fans_club": new_fans_club,
            "hamster_rmb": hamster_rmb,
        }
        derived = {
            "engagement": {
                "danmu_per_minute": round(danmu_num / (duration_seconds / 60), 2)
                if duration_seconds and isinstance(danmu_num, (int, float)) else None,
                "fan_gain_per_hour": round(add_fans / (duration_seconds / 3600), 2)
                if duration_seconds and isinstance(add_fans, (int, float)) else None,
            },
            "quality_flags": {
                "invalid_duration": bool(isinstance(live_time, int) and live_time < 0),
                "empty_session": bool(duration_seconds == 0 and not any((watched_count, danmu_num, add_fans, new_fans_club, hamster_rmb, max_online))),
            },
        }
        return {
            "schema": "bilibili.live_orchestrator.stop_live_data.v1",
            "live_key": self._mask_value(live_key, 8, 6),
            "summary": summary,
            "derived": derived,
            "raw": payload,
        }

    async def _get_live_overview(self) -> Dict[str, Any]:
        async with self.auth.get_client() as client:
            resp = await client.get("https://api.live.bilibili.com/xlive/app-blink/v1/date/Overview")
            data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(data.get("message", "Failed to fetch live overview"))
        payload = data.get("data") or {}
        graph = payload.get("graph") or []
        normalized = {}
        for item in graph:
            if not isinstance(item, dict):
                continue
            key = item.get("index") or item.get("name")
            if key:
                normalized[str(key)] = item
        return {
            "schema": "bilibili.live_orchestrator.live_overview.v1",
            "graph": graph,
            "graph_by_index": normalized,
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
        if content is None:
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

    async def update_live_title(
        self,
        title: str,
        room_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if (err := self._require_library()) or (err := self._require_auth()):
            return err
        if title is None or str(title).strip() == "":
            return self._failure("title is required")
        try:
            bundle = await self._get_live_room_bundle()
            resolved_room_id = int(room_id or bundle["room_id"])
            async with self.auth.get_client() as client:
                resp = await client.post(
                    "https://api.live.bilibili.com/room/v1/Room/update",
                    data={
                        "room_id": resolved_room_id,
                        "title": title,
                        "csrf": self.auth.bili_jct,
                        "csrf_token": self.auth.bili_jct,
                    },
                )
                data = resp.json()
            if data.get("code") != 0:
                return self._failure(
                    data.get("message", "Failed to update live title"),
                    schema="bilibili.live_orchestrator.update_live_title.v1",
                    room_id=resolved_room_id,
                    title=title,
                    raw=data,
                )
            return self._success(
                schema="bilibili.live_orchestrator.update_live_title.v1",
                room_id=resolved_room_id,
                title=title,
                audit_info=(data.get("data") or {}).get("audit_info"),
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to update live title: {exc}")

    async def pre_start_room_patch(
        self,
        room_id: Optional[int] = None,
        area_id: Optional[int] = None,
        announcement: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        if (err := self._require_library()) or (err := self._require_auth()):
            return err
        try:
            bundle = await self._get_live_room_bundle()
            resolved_room_id = int(room_id or bundle["room_id"])
            before = await self.get_live_room_profile(room_id=resolved_room_id)
            changes = []
            unsupported = []
            announcement_result = None
            title_result = None
            if announcement is not None:
                announcement_result = await self.update_live_announcement(content=announcement, room_id=resolved_room_id)
                changes.append("announcement")
            if title is not None:
                title_result = await self.update_live_title(title=title, room_id=resolved_room_id)
                changes.append("title")
            target_area = None
            if area_id is not None:
                current_area = await self._get_current_area(resolved_room_id)
                target_area = {
                    "current_area_id": (current_area or {}).get("id"),
                    "requested_area_id": int(area_id),
                    "will_apply_on_start": True,
                    "reason": "Bilibili startLive accepts area_v2; no separate confirmed pre-start area-write endpoint has been wired yet.",
                }
                changes.append("area")
            after = await self.get_live_room_profile(room_id=resolved_room_id)
            return self._success(
                schema="bilibili.live_orchestrator.pre_start_room_patch.v1",
                room_id=resolved_room_id,
                requested_changes={
                    "announcement": announcement,
                    "title": title,
                    "area_id": area_id,
                },
                applied={
                    "announcement": announcement_result,
                    "title": title_result,
                    "area": target_area,
                },
                unsupported=unsupported,
                before=before,
                after=after,
                changed_fields=changes,
            )
        except Exception as exc:
            return self._failure(f"Failed to patch pre-start room state: {exc}")

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
        title: Optional[str] = None,
        announcement: Optional[str] = None,
        obs_host: Optional[str] = None,
        obs_port: Optional[int] = None,
        obs_password: Optional[str] = None,
        obs_timeout: Optional[float] = None,
        watch_runtime: bool = False,
        watch_interval_seconds: float = 10.0,
        watch_samples: int = 6,
        watch_clear_log_first: bool = False,
        watch_include_overview: bool = False,
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

            pre_start_patch = None
            if title is not None or announcement is not None or area_id is not None:
                pre_start_patch = await self.pre_start_room_patch(
                    room_id=resolved_room_id,
                    area_id=resolved_area_id,
                    announcement=announcement,
                    title=title,
                )
                if not pre_start_patch.get("success"):
                    return self._failure(
                        "Pre-start room patch failed.",
                        schema="bilibili.live_orchestrator.start_live_session.v2",
                        room_id=resolved_room_id,
                        area_id=resolved_area_id,
                        pre_start_patch=pre_start_patch,
                    )
                applied = pre_start_patch.get("applied") or {}
                title_result = applied.get("title")
                announcement_result = applied.get("announcement")
                if isinstance(title_result, dict) and not title_result.get("success", False):
                    return self._failure(
                        "Requested live title update failed before start.",
                        schema="bilibili.live_orchestrator.start_live_session.v2",
                        room_id=resolved_room_id,
                        area_id=resolved_area_id,
                        pre_start_patch=pre_start_patch,
                    )
                if isinstance(announcement_result, dict) and not announcement_result.get("success", False):
                    return self._failure(
                        "Requested live announcement update failed before start.",
                        schema="bilibili.live_orchestrator.start_live_session.v2",
                        room_id=resolved_room_id,
                        area_id=resolved_area_id,
                        pre_start_patch=pre_start_patch,
                    )

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
                    schema="bilibili.live_orchestrator.start_live_session.v2",
                    room_id=resolved_room_id,
                    area_id=resolved_area_id,
                    pre_start_patch=pre_start_patch,
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
                    schema="bilibili.live_orchestrator.start_live_session.v2",
                    room_id=resolved_room_id,
                    area_id=resolved_area_id,
                    pre_start_patch=pre_start_patch,
                    start_response_keys=list(start_resp.keys()),
                )

            session_cache = self._update_session_cache(
                room_id=resolved_room_id,
                area_id=resolved_area_id,
                active=True,
                started_at=int(time.time()),
                live_key=start_resp.get("live_key"),
                title=title,
                announcement=announcement,
                pre_start_patch=pre_start_patch,
                restore_stream_service=original_service,
                bilibili_start_response=start_resp,
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
            runtime_watch = None
            if watch_runtime:
                runtime_watch = await self.watch_live_runtime(
                    room_id=resolved_room_id,
                    live_key=start_resp.get("live_key"),
                    use_session_cache=True,
                    include_overview=watch_include_overview,
                    interval_seconds=watch_interval_seconds,
                    samples=watch_samples,
                    clear_log_first=watch_clear_log_first,
                    reveal_sensitive=reveal_sensitive,
                )
            return self._success(
                schema="bilibili.live_orchestrator.start_live_session.v2",
                room_id=resolved_room_id,
                area_id=resolved_area_id,
                pre_start_patch=pre_start_patch,
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
                runtime_watch=runtime_watch,
                previous_obs_stream_service=original_service,
                session_cache={
                    "path": str(self.session_cache_path),
                    "active": session_cache.get("active"),
                    "room_id": session_cache.get("room_id"),
                    "has_live_key": bool(session_cache.get("live_key")),
                },
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
        use_session_cache: bool = True,
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
            cache = self._read_session_cache() if use_session_cache else None
            resolved_room_id = int(room_id or (cache or {}).get("room_id") or bundle["room_id"])
            resolved_live_key = live_key or (cache or {}).get("live_key")
            obs_stop = await self.obs.stop_stream(
                host=obs_host,
                port=obs_port,
                password=obs_password,
                timeout=obs_timeout,
            )
            room = await self._room(resolved_room_id)
            stop_resp = await room.stop()
            stop_stats = None
            if resolved_live_key:
                try:
                    stop_stats = await self._get_stop_live_data(resolved_live_key)
                except Exception as exc:
                    stop_stats = {"success": False, "message": str(exc), "live_key": self._mask_value(resolved_live_key, 8, 6)}
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
            elif restore_stream_service and cache and isinstance(cache.get("restore_stream_service"), dict):
                restore_service = cache.get("restore_stream_service") or {}
                restore_stream = restore_service.get("stream_service") or {}
                restore_settings = restore_stream.get("settings") or {}
                restore_resp = await self.obs.set_stream_service(
                    server=restore_settings.get("server", ""),
                    key=restore_settings.get("key", ""),
                    service_type=restore_stream.get("type") or "rtmp_custom",
                    reveal_sensitive=reveal_sensitive,
                    host=obs_host,
                    port=obs_port,
                    password=obs_password,
                    timeout=obs_timeout,
                    use_auth=bool(restore_settings.get("use_auth", False)),
                    bwtest=bool(restore_settings.get("bwtest", False)),
                )
            obs_status = await self.obs.get_status(
                host=obs_host,
                port=obs_port,
                password=obs_password,
                timeout=obs_timeout,
            )
            session_cache = None
            if use_session_cache:
                session_cache = self._update_session_cache(
                    room_id=resolved_room_id,
                    area_id=(cache or {}).get("area_id"),
                    active=False,
                    stopped_at=int(time.time()),
                    live_key=None,
                    last_live_key=resolved_live_key,
                    last_stop_stats=stop_stats,
                    last_bilibili_stop={
                        "status": stop_resp.get("status"),
                        "change": stop_resp.get("change"),
                        "raw": stop_resp,
                    },
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
                session_cache={
                    "path": str(self.session_cache_path),
                    "active": session_cache.get("active") if session_cache else None,
                    "room_id": session_cache.get("room_id") if session_cache else None,
                    "used_cached_live_key": bool((cache or {}).get("live_key")) and not bool(live_key),
                    "has_last_live_key": bool(session_cache.get("last_live_key")) if session_cache else False,
                },
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
            "update_live_title": self.update_live_title,
            "set_title": self.update_live_title,
            "pre_start_room_patch": self.pre_start_room_patch,
            "prepare_live_session": self.prepare_live_session,
            "start_live_session": self.start_live_session,
            "stop_live_session": self.stop_live_session,
            "get_live_session_cache": self.get_live_session_cache,
            "clear_live_session_cache": self.clear_live_session_cache,
            "get_live_runtime_log": self.get_live_runtime_log,
            "clear_live_runtime_log": self.clear_live_runtime_log,
            "get_live_runtime_stats": self.get_live_runtime_stats,
            "watch_live_runtime": self.watch_live_runtime,
            "recover_live_session": self.recover_live_session,
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
