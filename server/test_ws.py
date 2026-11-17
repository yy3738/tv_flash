"""模拟浏览器验证中继链路：登录 → /ws/web → open_session + snapshot_request → 收快照。

在 server/ 目录运行：
    .venv\\Scripts\\python.exe test_ws.py
"""

import asyncio
import json

import httpx
import websockets

BASE = "http://127.0.0.1:8080"
WS = "ws://127.0.0.1:8080/ws/web"
DEVICE = "6c8e52f62d4b4ed4a19816e87a679717"


async def main():
    async with httpx.AsyncClient() as c:
        r = await c.post(BASE + "/api/login", json={"username": "admin", "password": "admin123"})
        print("login", r.status_code)
        cookie = "; ".join(f"{k}={v}" for k, v in c.cookies.items())
        devices = (await c.get(BASE + "/api/devices")).json().get("devices", [])
        print("devices:", devices)

    try:
        ws = await websockets.connect(WS, additional_headers=[("Cookie", cookie)])
    except TypeError:
        ws = await websockets.connect(WS, extra_headers=[("Cookie", cookie)])

    await ws.send(json.dumps({"type": "open_session", "deviceId": DEVICE}))
    await ws.send(json.dumps({"type": "snapshot_request", "deviceId": DEVICE}))
    for _ in range(6):
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=6)
        except asyncio.TimeoutError:
            print("timeout")
            break
        if isinstance(msg, bytes):
            print("GOT_IMAGE len=", len(msg), "first=", msg[0])
            with open("shot.jpg", "wb") as f:
                f.write(msg[1:])
            print("saved shot.jpg")
            break
        print("json:", msg)
    await ws.close()


asyncio.run(main())
