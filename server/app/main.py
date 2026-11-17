import time
import uuid

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from .auth import ensure_admin, hash_token, new_token, verify_password
from .config import SECRET_KEY, WEB_DIST
from .db import db, init_db
from .hub import Hub

app = FastAPI(title="TV Flash")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
hub = Hub()


@app.on_event("startup")
def _startup():
    init_db()
    ensure_admin()


def require_login(request: Request) -> str:
    uid = request.session.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="unauthorized")
    return uid


# ---------------- REST ----------------

class LoginIn(BaseModel):
    username: str
    password: str


class DeviceIn(BaseModel):
    name: str


@app.post("/api/login")
def login(body: LoginIn, request: Request):
    with db() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM sys_account "
            "WHERE deleted=1 AND username=?",
            (body.username,),
        ).fetchone()
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid credentials")
    request.session["uid"] = row["id"]
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/devices")
def list_devices(request: Request):
    uid = require_login(request)
    with db() as conn:
        rows = conn.execute(
            "SELECT id, name, online, last_seen FROM biz_device "
            "WHERE deleted=1 AND account_id=? ORDER BY create_time DESC",
            (uid,),
        ).fetchall()
    return {"ok": True, "devices": [dict(r) for r in rows]}


@app.post("/api/devices")
def create_device(body: DeviceIn, request: Request):
    uid = require_login(request)
    token = new_token()
    device_id = uuid.uuid4().hex
    now = int(time.time() * 1000)
    with db() as conn:
        conn.execute(
            "INSERT INTO biz_device "
            "(id, account_id, name, token_hash, online, version, deleted, create_time, update_time) "
            "VALUES (?, ?, ?, ?, 0, 0, 1, ?, ?)",
            (device_id, uid, body.name, hash_token(token), now, now),
        )
    # token 仅此一次返回，请立即填入电视端
    return {"ok": True, "deviceId": device_id, "token": token}


@app.post("/api/devices/{device_id}/kick")
async def kick_device(device_id: str, request: Request):
    require_login(request)
    with db() as conn:
        conn.execute("UPDATE biz_device SET online=0 WHERE id=?", (device_id,))
    ws = hub.tv.get(device_id)
    if ws is not None:
        try:
            await ws.close()
        except Exception:
            pass
    await hub.notify_status(device_id, False)
    return {"ok": True}


@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: str, request: Request):
    require_login(request)
    with db() as conn:
        conn.execute(
            "UPDATE biz_device SET deleted=2, online=0 WHERE id=?", (device_id,)
        )
    ws = hub.tv.get(device_id)
    if ws is not None:
        try:
            await ws.close()
        except Exception:
            pass
    await hub.notify_status(device_id, False)
    return {"ok": True}


# ---------------- WebSocket: 浏览器 ----------------

_FORWARD_KEYS = ("x", "y", "x1", "y1", "x2", "y2", "durationMs", "key", "reqId")


@app.websocket("/ws/web")
async def ws_web(ws: WebSocket):
    session = ws.scope.get("session") or {}
    if not session.get("uid"):
        await ws.close(code=4401)
        return
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")
            device_id = msg.get("deviceId")

            if mtype == "open_session":
                hub.subscribe(device_id, ws)
                await ws.send_json({
                    "type": "session_state",
                    "deviceId": device_id,
                    "state": "active" if hub.is_online(device_id) else "offline",
                })
                await hub.send_to_tv(device_id, {"type": "open_session"})

            elif mtype == "close_session":
                await hub.send_to_tv(device_id, {"type": "close_session"})
                hub.unsubscribe(device_id, ws)

            elif mtype in ("snapshot_request", "tap", "swipe", "system_key"):
                fwd = {"type": mtype}
                for key in _FORWARD_KEYS:
                    if key in msg:
                        fwd[key] = msg[key]
                if not await hub.send_to_tv(device_id, fwd):
                    await ws.send_json({"type": "error", "message": "device offline"})
    except WebSocketDisconnect:
        hub.unsubscribe_all(ws)
    except Exception:
        hub.unsubscribe_all(ws)


# ---------------- WebSocket: 电视端 ----------------

@app.websocket("/ws/tv")
async def ws_tv(ws: WebSocket):
    token = ws.query_params.get("token", "")
    with db() as conn:
        row = conn.execute(
            "SELECT id FROM biz_device WHERE deleted=1 AND token_hash=?",
            (hash_token(token),),
        ).fetchone()
    if row is None:
        await ws.close(code=4403)
        return

    device_id = row["id"]
    await ws.accept()
    hub.register_tv(device_id, ws)
    with db() as conn:
        conn.execute(
            "UPDATE biz_device SET online=1, last_seen=? WHERE id=?",
            (int(time.time() * 1000), device_id),
        )
    await hub.notify_status(device_id, True)

    try:
        while True:
            data = await ws.receive()
            if data.get("type") == "websocket.disconnect":
                break
            if data.get("bytes") is not None:
                await hub.broadcast_bytes(device_id, data["bytes"])
            elif data.get("text") is not None:
                await hub.broadcast_raw_text(device_id, data["text"])
    except Exception:
        pass
    finally:
        hub.unregister_tv(device_id, ws)
        with db() as conn:
            conn.execute("UPDATE biz_device SET online=0 WHERE id=?", (device_id,))
        await hub.notify_status(device_id, False)


# ---------------- 静态前端 ----------------

if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="web")
