"""Bilibili video uploading and publishing module."""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
import logging

import httpx

from .auth import BilibiliAuth
from .utils import DEFAULT_HEADERS, API_BASE

_logger = logging.getLogger("bilibili.publisher")


# Publishing API endpoints
PREUPLOAD_URL = "https://member.bilibili.com/preupload"
MEMBER_API_BASE = "https://member.bilibili.com"
ADD_VIDEO_URL = f"{MEMBER_API_BASE}/x/vu/web/add"
EDIT_VIDEO_URL = f"{MEMBER_API_BASE}/x/vu/web/edit"
COVER_UPLOAD_URL = f"{MEMBER_API_BASE}/x/vu/web/cover/up"


class BilibiliPublisher:
    """Publish videos to Bilibili.

    Supports uploading videos, setting metadata, scheduling publications,
    and managing drafts.
    """

    def __init__(self, auth: BilibiliAuth):
        """Initialize BilibiliPublisher.

        Args:
            auth: BilibiliAuth instance (required for publishing).

        Raises:
            ValueError: If auth is not provided or not authenticated.
        """
        if not auth or not auth.is_authenticated:
            raise ValueError("Valid authentication is required for publishing")
        self.auth = auth

    def _get_client(self) -> httpx.AsyncClient:
        """Get an authenticated HTTP client."""
        return self.auth.get_client()

    @staticmethod
    def _validate_publish_inputs(
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category: str = "171",
    ) -> Dict[str, Any]:
        title = (title or "").strip()
        description = description or ""
        tags = [str(tag).strip() for tag in (tags or []) if str(tag).strip()]
        if not title:
            return {"success": False, "message": "title is required"}
        if len(title) > 80:
            return {"success": False, "message": "Title must be 80 characters or less"}
        if len(description) > 2000:
            return {"success": False, "message": "Description must be 2000 characters or less"}
        if len(tags) > 12:
            return {"success": False, "message": "At most 12 tags are allowed"}
        if not str(category).strip().isdigit():
            return {"success": False, "message": f"Invalid category/tid: {category}"}
        return {
            "success": True,
            "title": title,
            "description": description,
            "tags": tags or ["bilibili"],
            "category": str(category).strip(),
        }

    @staticmethod
    def _failure(message: str, *, stage: str, error_type: str, detail: Any = None, **kwargs) -> Dict[str, Any]:
        payload = {
            "success": False,
            "message": message,
            "stage": stage,
            "error_type": error_type,
        }
        if detail is not None:
            payload["detail"] = detail
        payload.update(kwargs)
        return payload

    @staticmethod
    def _parse_json_response(resp: httpx.Response, default_error: str) -> Dict[str, Any]:
        if resp.status_code != 200:
            raise RuntimeError(f"http_error|HTTP {resp.status_code}: {resp.text[:500]}")
        try:
            return resp.json()
        except Exception:
            text = resp.text[:500]
            error_type = "non_json_response"
            if "错误号: 412" in text or "security control policy" in text:
                error_type = "risk_control"
            raise RuntimeError(f"{error_type}|{default_error}: {text}")

    async def inspect_video(self, bvid: str) -> Dict[str, Any]:
        async with self._get_client() as client:
            resp = await client.get(
                f"{API_BASE}/x/web-interface/view",
                params={"bvid": bvid},
            )
            data = self._parse_json_response(resp, "Video inspection failed")

        if data.get("code") != 0:
            return self._failure(
                data.get("message", "Video not found"),
                stage="inspect",
                error_type="api_error",
                bvid=bvid,
                detail=data,
            )

        video = data.get("data", {})
        return {
            "success": True,
            "bvid": bvid,
            "aid": video.get("aid"),
            "title": video.get("title"),
            "description": video.get("desc"),
            "tid": video.get("tid"),
            "copyright": video.get("copyright"),
            "tags": [t.get("tag_name") for t in video.get("tags", []) if t.get("tag_name")],
            "cover": video.get("pic"),
            "raw": video,
        }

    async def preview_upload(
        self,
        file_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category: str = "171",
        cover_path: Optional[str] = None,
        dynamic: str = "",
    ) -> Dict[str, Any]:
        checks = self._validate_publish_inputs(title=title, description=description, tags=tags, category=category)
        if not checks.get("success"):
            return self._failure(checks.get("message", "Validation failed"), stage="validate", error_type="validation_error")
        if not os.path.exists(file_path):
            return self._failure(f"File not found: {file_path}", stage="validate", error_type="file_missing", file_path=file_path)

        file_size = os.path.getsize(file_path)
        return {
            "success": True,
            "mode": "preview",
            "stage": "validated",
            "file": {
                "path": file_path,
                "size": file_size,
                "name": os.path.basename(file_path),
            },
            "cover": {
                "path": cover_path,
                "exists": bool(cover_path and os.path.exists(cover_path)),
            },
            "payload": {
                "title": checks["title"],
                "description": checks["description"],
                "tags": checks["tags"],
                "tid": int(checks["category"]),
                "dynamic": dynamic,
            },
        }

    async def upload(
        self,
        file_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category: str = "171",
        cover_path: Optional[str] = None,
        dynamic: str = "",
        no_reprint: int = 1,
        open_elec: int = 0,
    ) -> Dict[str, Any]:
        """Upload and publish a video to Bilibili.

        Args:
            file_path: Path to the video file.
            title: Video title (max 80 chars).
            description: Video description (max 2000 chars).
            tags: List of tags (max 12 tags, each max 20 chars).
            category: Category TID (default '171' for electronic gaming).
            cover_path: Path to cover image (optional).
            dynamic: Dynamic/feed text.
            no_reprint: 1 = original, 0 = repost.
            open_elec: 1 = enable charging, 0 = disable.

        Returns:
            Upload result with video info.
        """
        if not os.path.exists(file_path):
            return {"success": False, "message": f"File not found: {file_path}"}

        checks = self._validate_publish_inputs(title=title, description=description, tags=tags, category=category)
        if not checks.get("success"):
            return checks
        title = checks["title"]
        description = checks["description"]
        tags = checks["tags"]
        category = checks["category"]

        # Step 1: Pre-upload to get upload params
        preupload_result = await self._preupload(file_path)
        if not preupload_result.get("success"):
            return preupload_result

        # Step 2: Upload video file
        upload_result = await self._upload_file(
            file_path,
            preupload_result,
        )
        if not upload_result.get("success"):
            return upload_result

        # Step 3: Upload cover if provided
        cover_url = ""
        if cover_path and os.path.exists(cover_path):
            cover_result = await self._upload_cover(cover_path)
            if cover_result.get("success"):
                cover_url = cover_result.get("url", "")

        # Step 4: Submit video
        submit_result = await self._submit_video(
            filename=upload_result["filename"],
            title=title,
            desc=description,
            tags=tags,
            tid=int(category),
            cover=cover_url,
            dynamic=dynamic,
            no_reprint=no_reprint,
            open_elec=open_elec,
        )

        if submit_result.get("success"):
            submit_result.update({
                "mode": "publish",
                "file_path": file_path,
                "cover_path": cover_path,
                "title": title,
                "tags": tags,
                "tid": int(category),
            })
        return submit_result

    async def draft(
        self,
        file_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category: str = "171",
        cover_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save a video as draft.

        Args:
            file_path: Path to the video file.
            title: Video title.
            description: Video description.
            tags: List of tags.
            category: Category TID.
            cover_path: Path to cover image.

        Returns:
            Draft save result.
        """
        if not os.path.exists(file_path):
            return self._failure(f"File not found: {file_path}", stage="validate", error_type="file_missing", file_path=file_path)

        checks = self._validate_publish_inputs(title=title, description=description, tags=tags, category=category)
        if not checks.get("success"):
            return self._failure(checks.get("message", "Validation failed"), stage="validate", error_type="validation_error")
        title = checks["title"]
        description = checks["description"]
        tags = checks["tags"]
        category = checks["category"]

        # Upload video file
        preupload_result = await self._preupload(file_path)
        if not preupload_result.get("success"):
            return preupload_result

        upload_result = await self._upload_file(file_path, preupload_result)
        if not upload_result.get("success"):
            return upload_result

        # Upload cover if provided
        cover_url = ""
        if cover_path and os.path.exists(cover_path):
            cover_result = await self._upload_cover(cover_path)
            if cover_result.get("success"):
                cover_url = cover_result.get("url", "")

        # Save as draft (use the same add API with draft=1)
        async with self._get_client() as client:
            resp = await client.post(
                ADD_VIDEO_URL,
                params={"csrf": self.auth.csrf},
                json={
                    "videos": [{
                        "filename": upload_result["filename"],
                        "title": title,
                        "desc": "",
                    }],
                    "title": title,
                    "desc": description,
                    "tag": ",".join(tags),
                    "tid": int(category),
                    "cover": cover_url,
                    "copyright": 1,
                    "no_reprint": 1,
                    "open_elec": 0,
                    "draft": 1,
                    "csrf": self.auth.csrf,
                },
            )
            try:
                data = self._parse_json_response(resp, "Draft save failed")
            except Exception as exc:
                message = str(exc)
                error_type, _, detail = message.partition("|")
                return self._failure(detail or message, stage="submit", error_type=error_type or "unknown_error")

        if data.get("code") != 0:
            return self._failure(data.get("message", "Draft save failed"), stage="submit", error_type="api_error", detail=data)

        return {
            "success": True,
            "mode": "draft",
            "stage": "submitted",
            "draft_id": data.get("data", {}).get("aid"),
            "title": title,
            "tags": tags,
            "tid": int(category),
            "message": "Draft saved successfully",
            "result": data.get("data", {}),
        }

    async def schedule(
        self,
        file_path: str,
        title: str,
        schedule_time: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category: str = "171",
        cover_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Schedule a video for future publication.

        Args:
            file_path: Path to the video file.
            title: Video title.
            schedule_time: Scheduled publish time (ISO 8601 format).
            description: Video description.
            tags: List of tags.
            category: Category TID.
            cover_path: Path to cover image.

        Returns:
            Schedule result.
        """
        import datetime

        if not os.path.exists(file_path):
            return self._failure(f"File not found: {file_path}", stage="validate", error_type="file_missing", file_path=file_path)

        # Parse schedule time
        try:
            dt = datetime.datetime.fromisoformat(schedule_time.replace("Z", "+00:00"))
            timestamp = int(dt.timestamp())
        except ValueError:
            return self._failure(
                f"Invalid schedule time format: {schedule_time}",
                stage="validate",
                error_type="validation_error",
                schedule_time=schedule_time,
            )

        checks = self._validate_publish_inputs(title=title, description=description, tags=tags, category=category)
        if not checks.get("success"):
            return checks
        title = checks["title"]
        description = checks["description"]
        tags = checks["tags"]
        category = checks["category"]

        # Upload video file
        preupload_result = await self._preupload(file_path)
        if not preupload_result.get("success"):
            return preupload_result

        upload_result = await self._upload_file(file_path, preupload_result)
        if not upload_result.get("success"):
            return upload_result

        # Upload cover if provided
        cover_url = ""
        if cover_path and os.path.exists(cover_path):
            cover_result = await self._upload_cover(cover_path)
            if cover_result.get("success"):
                cover_url = cover_result.get("url", "")

        # Submit with schedule
        submit_result = await self._submit_video(
            filename=upload_result["filename"],
            title=title,
            desc=description,
            tags=tags,
            tid=int(category),
            cover=cover_url,
            dtime=timestamp,
        )

        if submit_result.get("success"):
            submit_result.update({
                "mode": "schedule",
                "scheduled_time": schedule_time,
                "file_path": file_path,
                "cover_path": cover_path,
                "title": title,
                "tags": tags,
                "tid": int(category),
            })

        return submit_result

    async def edit(
        self,
        bvid: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        cover_path: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Edit an existing video's metadata.

        Args:
            bvid: BV number of the video to edit.
            title: New title (if changing).
            description: New description (if changing).
            tags: New tags (if changing).
            cover_path: New cover image path (if changing).
            file_path: Path to video file (required for re-upload).

        Returns:
            Edit result.
        """
        inspected = await self.inspect_video(bvid)
        if not inspected.get("success"):
            return inspected
        video = inspected["raw"]

        # Re-upload video file to get a fresh filename
        if file_path and os.path.exists(file_path):
            preupload_result = await self._preupload(file_path)
            if not preupload_result.get("success"):
                return preupload_result
            upload_result = await self._upload_file(file_path, preupload_result)
            if not upload_result.get("success"):
                return upload_result
            new_filename = upload_result["filename"]
        else:
            return {"success": False, "message": "file_path is required for editing (B站 requires re-upload)"}

        # Build edit payload with videos info
        new_title = title or video.get("title")
        videos = [{
            "filename": new_filename,
            "title": new_title,
            "desc": "",
        }]

        edit_data = {
            "aid": video["aid"],
            "videos": videos,
            "title": new_title,
            "desc": description if description is not None else video.get("desc", ""),
            "tag": ",".join(tags) if tags else ",".join(
                t.get("tag_name", "") for t in video.get("tags", []) if t.get("tag_name")
            ),
            "tid": video.get("tid"),
            "copyright": video.get("copyright", 1),
            "csrf": self.auth.csrf,
        }

        # Upload new cover if provided
        if cover_path and os.path.exists(cover_path):
            cover_result = await self._upload_cover(cover_path)
            if cover_result.get("success"):
                edit_data["cover"] = cover_result.get("url", "")

        async with self._get_client() as client:
            resp = await client.post(
                EDIT_VIDEO_URL,
                params={"csrf": self.auth.csrf},
                json=edit_data,
            )
            try:
                result = self._parse_json_response(resp, "Edit failed")
            except Exception as exc:
                message = str(exc)
                error_type, _, detail = message.partition("|")
                return self._failure(detail or message, stage="submit", error_type=error_type or "unknown_error", bvid=bvid)

        if result.get("code") != 0:
            return self._failure(result.get("message", "Edit failed"), stage="submit", error_type="api_error", bvid=bvid, detail=result)

        return {
            "success": True,
            "mode": "edit",
            "stage": "submitted",
            "bvid": bvid,
            "title": new_title,
            "tags": tags if tags else [t.get("tag_name", "") for t in video.get("tags", []) if t.get("tag_name")],
            "tid": video.get("tid"),
            "message": "Video edited successfully",
            "result": result.get("data", {}),
        }

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute a publisher action.

        Args:
            action: Action name ('upload', 'draft', 'schedule', 'edit').
            **kwargs: Additional parameters for the action.

        Returns:
            Action result dict.
        """
        actions = {
            "upload": self.upload,
            "draft": self.draft,
            "schedule": self.schedule,
            "edit": self.edit,
            "inspect_video": self.inspect_video,
            "preview_upload": self.preview_upload,
        }

        handler = actions.get(action)
        if not handler:
            return {"success": False, "message": f"Unknown action: {action}"}

        import inspect
        sig = inspect.signature(handler)
        valid_params = {k: v for k, v in kwargs.items() if k in sig.parameters}

        return await handler(**valid_params)

    async def _preupload(self, file_path: str) -> Dict[str, Any]:
        """Request pre-upload parameters from Bilibili.

        Args:
            file_path: Path to the video file.

        Returns:
            Pre-upload parameters dict.
        """
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)

        async with self._get_client() as client:
            resp = await client.get(
                PREUPLOAD_URL,
                params={
                    "name": file_name,
                    "size": file_size,
                    "r": "upos",
                    "profile": "ugcupos/bup",
                    "ssl": 0,
                    "version": "2.14.0",
                    "build": 2140000,
                    "upcdn": "bda2",
                    "probe_version": 20221109,
                },
            )
            try:
                data = self._parse_json_response(resp, "Pre-upload failed")
            except Exception as exc:
                return {"success": False, "message": str(exc)}

        if "upos_uri" not in data:
            return {"success": False, "message": "Pre-upload failed"}

        return {
            "success": True,
            "upos_uri": data["upos_uri"],
            "auth": data.get("auth"),
            "biz_id": data.get("biz_id"),
            "chunk_size": data.get("chunk_size", 4 * 1024 * 1024),
            "endpoints": data.get("endpoints", []),
            "file_size": file_size,
            "file_name": file_name,
        }

    async def _upload_file(
        self,
        file_path: str,
        preupload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Upload a video file in chunks.

        Args:
            file_path: Path to the video file.
            preupload: Pre-upload parameters from _preupload().

        Returns:
            Upload result with filename.
        """
        upos_uri = preupload["upos_uri"]
        auth = preupload.get("auth")
        biz_id = preupload.get("biz_id")
        chunk_size = preupload.get("chunk_size", 4 * 1024 * 1024)
        file_size = preupload["file_size"]

        # Extract upos key from URI
        upos_key = upos_uri.replace("upos://", "")
        filename = upos_key.split("/")[-1].split(".")[0]

        # Calculate chunk count
        chunk_count = (file_size + chunk_size - 1) // chunk_size

        # Init upload
        upload_base = f"https://upos-sz-upcdnbda2.bilivideo.com/{upos_key}"

        async with self._get_client() as client:
            # Fetch upload ID
            resp = await client.post(
                upload_base,
                params={
                    "uploads": "",
                    "output": "json",
                },
                headers={"X-Upos-Auth": auth} if auth else {},
            )

            try:
                init_data = self._parse_json_response(resp, "Failed to initialize upload")
                upload_id = init_data.get("upload_id", "")
            except Exception as exc:
                return {"success": False, "message": str(exc)}

        # Upload chunks
        with open(file_path, "rb") as f:
            for chunk_idx in range(chunk_count):
                chunk_data = f.read(chunk_size)
                start = chunk_idx * chunk_size
                end = min(start + len(chunk_data), file_size)

                async with self._get_client() as client:
                    resp = await client.put(
                        upload_base,
                        params={
                            "partNumber": chunk_idx + 1,
                            "uploadId": upload_id,
                            "chunk": chunk_idx,
                            "chunks": chunk_count,
                            "size": len(chunk_data),
                            "start": start,
                            "end": end,
                            "total": file_size,
                        },
                        headers={
                            "X-Upos-Auth": auth or "",
                            "Content-Type": "application/octet-stream",
                        },
                        content=chunk_data,
                    )

                    if resp.status_code not in (200, 202):
                        return {
                            "success": False,
                            "message": f"Upload chunk {chunk_idx + 1}/{chunk_count} failed",
                        }

        # Complete upload
        parts = [{"partNumber": i + 1, "eTag": "etag"} for i in range(chunk_count)]

        async with self._get_client() as client:
            resp = await client.post(
                upload_base,
                params={
                    "output": "json",
                    "name": preupload["file_name"],
                    "profile": "ugcupos/bup",
                    "uploadId": upload_id,
                    "biz_id": biz_id or 0,
                },
                json={"parts": parts},
                headers={"X-Upos-Auth": auth or ""},
            )

        return {
            "success": True,
            "filename": filename,
            "upos_uri": upos_uri,
        }

    async def _upload_cover(self, cover_path: str) -> Dict[str, Any]:
        """Upload a cover image.

        Args:
            cover_path: Path to the cover image.

        Returns:
            Upload result with cover URL.
        """
        if not os.path.exists(cover_path):
            return {"success": False, "message": f"Cover file not found: {cover_path}"}

        with open(cover_path, "rb") as f:
            cover_data = f.read()

        # Detect MIME type
        if cover_path.lower().endswith(".png"):
            mime_type = "image/png"
        elif cover_path.lower().endswith((".jpg", ".jpeg")):
            mime_type = "image/jpeg"
        else:
            mime_type = "image/jpeg"

        import base64
        cover_b64 = f"data:{mime_type};base64,{base64.b64encode(cover_data).decode()}"

        async with self._get_client() as client:
            resp = await client.post(
                COVER_UPLOAD_URL,
                data={
                    "cover": cover_b64,
                    "csrf": self.auth.csrf,
                },
            )
            try:
                data = self._parse_json_response(resp, "Cover upload failed")
            except Exception as exc:
                return {"success": False, "message": str(exc)}

        if data.get("code") != 0:
            return {"success": False, "message": data.get("message", "Cover upload failed")}

        return {
            "success": True,
            "url": data.get("data", {}).get("url", ""),
        }

    async def _submit_video(
        self,
        filename: str,
        title: str,
        desc: str = "",
        tags: Optional[List[str]] = None,
        tid: int = 171,
        cover: str = "",
        dynamic: str = "",
        no_reprint: int = 1,
        open_elec: int = 0,
        dtime: int = 0,
    ) -> Dict[str, Any]:
        """Submit a video for publishing.

        Args:
            filename: Uploaded video filename.
            title: Video title.
            desc: Description.
            tags: Tags list.
            tid: Category TID.
            cover: Cover image URL.
            dynamic: Dynamic text.
            no_reprint: Original flag.
            open_elec: Charging flag.
            dtime: Scheduled publish timestamp (0 = immediate).

        Returns:
            Submit result.
        """
        tags = tags or ["bilibili"]

        payload = {
            "videos": [{
                "filename": filename,
                "title": title,
                "desc": "",
            }],
            "title": title,
            "desc": desc,
            "tag": ",".join(tags),
            "tid": tid,
            "cover": cover,
            "dynamic": dynamic,
            "copyright": 1 if no_reprint else 2,
            "no_reprint": no_reprint,
            "open_elec": open_elec,
            "csrf": self.auth.csrf,
        }

        if dtime > 0:
            payload["dtime"] = dtime

        async with self._get_client() as client:
            params = {"csrf": self.auth.csrf}
            resp = await client.post(
                ADD_VIDEO_URL,
                params=params,
                json=payload,
            )
            try:
                data = self._parse_json_response(resp, "Submit failed")
            except Exception as exc:
                message = str(exc)
                error_type, _, detail = message.partition("|")
                return self._failure(detail or message, stage="submit", error_type=error_type or "unknown_error")

        if data.get("code") != 0:
            return self._failure(data.get("message", "Submit failed"), stage="submit", error_type="api_error", detail=data)

        result_data = data.get("data", {})
        return {
            "success": True,
            "stage": "submitted",
            "aid": result_data.get("aid"),
            "bvid": result_data.get("bvid"),
            "message": "Video published successfully",
            "result": result_data,
        }
