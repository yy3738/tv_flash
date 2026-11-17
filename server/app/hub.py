from typing import Dict, Set

from fastapi import WebSocket


class Hub:
    """维护电视端连接与浏览器订阅，并做双向中继。"""

    def __init__(self) -> None:
        self.tv: Dict[str, WebSocket] = {}
        self.subs: Dict[str, Set[WebSocket]] = {}

    # --- 电视端连接 ---
    def register_tv(self, device_id: str, ws: WebSocket) -> None:
        self.tv[device_id] = ws

    def unregister_tv(self, device_id: str, ws: WebSocket) -> None:
        if self.tv.get(device_id) is ws:
            self.tv.pop(device_id, None)

    def is_online(self, device_id: str) -> bool:
        return device_id in self.tv

    # --- 浏览器订阅 ---
    def subscribe(self, device_id: str, ws: WebSocket) -> None:
        self.subs.setdefault(device_id, set()).add(ws)

    def unsubscribe(self, device_id: str, ws: WebSocket) -> None:
        group = self.subs.get(device_id)
        if group:
            group.discard(ws)
            if not group:
                self.subs.pop(device_id, None)

    def unsubscribe_all(self, ws: WebSocket) -> None:
        for device_id in list(self.subs.keys()):
            self.unsubscribe(device_id, ws)

    # --- 转发 ---
    async def send_to_tv(self, device_id: str, message: dict) -> bool:
        ws = self.tv.get(device_id)
        if ws is None:
            return False
        try:
            await ws.send_json(message)
            return True
        except Exception:
            return False

    async def broadcast_json(self, device_id: str, message: dict) -> None:
        for ws in list(self.subs.get(device_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                self.subs.get(device_id, set()).discard(ws)

    async def broadcast_bytes(self, device_id: str, data: bytes) -> None:
        for ws in list(self.subs.get(device_id, set())):
            try:
                await ws.send_bytes(data)
            except Exception:
                self.subs.get(device_id, set()).discard(ws)

    async def broadcast_raw_text(self, device_id: str, text: str) -> None:
        for ws in list(self.subs.get(device_id, set())):
            try:
                await ws.send_text(text)
            except Exception:
                self.subs.get(device_id, set()).discard(ws)

    async def notify_status(self, device_id: str, online: bool) -> None:
        await self.broadcast_json(
            device_id,
            {"type": "device_status", "deviceId": device_id, "online": online},
        )
