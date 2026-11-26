"""自动刷新链路压测：模拟浏览器以固定间隔连收 N 帧快照并统计。

在 server/ 目录运行：
    .venv\\Scripts\\python.exe test_refresh.py
"""

import asyncio
import json
import statistics
import time

import httpx
import websockets

BASE = "http://127.0.0.1:8080"
WS = "ws://127.0.0.1:8080/ws/web"
DEVICE = "6c8e52f62d4b4ed4a19816e87a679717"
INTERVAL = 1.5
FRAMES = 10
TIMEOUT = 6.0


async def main():
    async with httpx.AsyncClient() as c:
        r = await c.post(BASE + "/api/login", json={"username": "admin", "password": "admin123"})
        print("login", r.status_code)
        cookie = "; ".join(f"{k}={v}" for k, v in c.cookies.items())

    try:
        ws = await websockets.connect(WS, additional_headers=[("Cookie", cookie)])
    except TypeError:
        ws = await websockets.connect(WS, extra_headers=[("Cookie", cookie)])

    await ws.send(json.dumps({"type": "open_session", "deviceId": DEVICE}))
    sizes = []
    times = []
    for i in range(FRAMES):
        t0 = time.monotonic()
        await ws.send(json.dumps({"type": "snapshot_request", "deviceId": DEVICE}))
        img = None
        while time.monotonic() - t0 < TIMEOUT:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT)
            except asyncio.TimeoutError:
                break
            if isinstance(msg, bytes):
                img = msg
                break
        if img:
            sizes.append(len(img))
            times.append(time.monotonic() - t0)
            print(f"frame {i + 1}: {len(img)}B in {times[-1]:.2f}s")
        else:
            print(f"frame {i + 1}: TIMEOUT")
        await asyncio.sleep(max(0.0, INTERVAL - (time.monotonic() - t0)))
    await ws.close()

    if sizes:
        print(f"RESULT ok={len(sizes)}/{FRAMES} "
              f"avg_size={statistics.mean(sizes):.0f}B "
              f"avg_rt={statistics.mean(times):.2f}s max_rt={max(times):.2f}s")
    else:
        print("RESULT NO_FRAMES")


asyncio.run(main())
