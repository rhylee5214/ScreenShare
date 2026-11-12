import os
import re
import time
import secrets
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="ScreenShare")
app.mount("/static", StaticFiles(directory="static"), name="static")

ADMIN_KEY = os.getenv("ADMIN_KEY", "")
TURN_URL = os.getenv("TURN_URL", "")
TURN_USERNAME = os.getenv("TURN_USERNAME", "")
TURN_CREDENTIAL = os.getenv("TURN_CREDENTIAL", "")

requests_by_id: Dict[str, Dict[str, Any]] = {}
peers: Dict[str, Dict[str, WebSocket]] = {}

class CreateRequest(BaseModel):
    device_id: str

class DeviceResponse(BaseModel):
    device_id: str
    decision: str

def require_admin(authorization: str | None):
    if not ADMIN_KEY:
        raise HTTPException(503, "ADMIN_KEY is not configured on the server.")
    if authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(401, "Invalid admin key.")

def get_ice_servers():
    servers = [{"urls": ["stun:stun.l.google.com:19302"]}]
    if TURN_URL and TURN_USERNAME and TURN_CREDENTIAL:
        servers.append({
            "urls": [u.strip() for u in TURN_URL.split(",") if u.strip()],
            "username": TURN_USERNAME,
            "credential": TURN_CREDENTIAL
        })
    return servers

@app.get("/", response_class=HTMLResponse)
async def admin_home():
    return open("templates/admin.html", encoding="utf-8").read()

@app.get("/share/{request_id}", response_class=HTMLResponse)
async def share_page(request_id: str):
    item = requests_by_id.get(request_id)
    if not item or item["status"] != "approved":
        raise HTTPException(404, "This sharing request is not approved or has expired.")
    return open("templates/share.html", encoding="utf-8").read()

@app.get("/view/{request_id}", response_class=HTMLResponse)
async def view_page(request_id: str):
    item = requests_by_id.get(request_id)
    if not item or item["status"] != "approved":
        raise HTTPException(404, "This sharing request is not approved or has expired.")
    return open("templates/view.html", encoding="utf-8").read()

@app.get("/api/config")
async def config():
    return {"ice_servers": get_ice_servers()}

@app.post("/api/requests")
async def create_request(body: CreateRequest, authorization: str | None = Header(default=None)):
    require_admin(authorization)
    if not re.fullmatch(r"[a-f0-9]{32}", body.device_id):
        raise HTTPException(400, "Invalid device ID.")
    # Keep only recent requests in this single-process demo.
    cutoff = time.time() - 3600
    for rid in list(requests_by_id):
        if requests_by_id[rid]["created"] < cutoff:
            requests_by_id.pop(rid, None)
            peers.pop(rid, None)
    request_id = secrets.token_urlsafe(24)
    requests_by_id[request_id] = {
        "device_id": body.device_id,
        "status": "pending",
        "created": time.time()
    }
    return {"request_id": request_id, "status": "pending"}

@app.get("/api/poll/{device_id}")
async def poll_device(device_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", device_id):
        raise HTTPException(400, "Invalid device ID.")
    for rid, item in requests_by_id.items():
        if item["device_id"] == device_id and item["status"] == "pending":
            item["notified"] = True
            return {"request_id": rid, "status": "pending"}
    return {"status": "idle"}

@app.post("/api/respond/{request_id}")
async def respond_device(request_id: str, body: DeviceResponse):
    item = requests_by_id.get(request_id)
    if not item or item["device_id"] != body.device_id:
        raise HTTPException(404, "Request not found.")
    if item["status"] != "pending":
        raise HTTPException(409, "This request has already been answered.")
    if body.decision not in ("allow", "deny"):
        raise HTTPException(400, "Decision must be allow or deny.")
    item["status"] = "approved" if body.decision == "allow" else "denied"
    return {"status": item["status"]}

@app.get("/api/requests/{request_id}")
async def request_status(request_id: str, authorization: str | None = Header(default=None)):
    require_admin(authorization)
    item = requests_by_id.get(request_id)
    if not item:
        raise HTTPException(404, "Request not found or expired.")
    return {"status": item["status"]}

@app.websocket("/ws/{request_id}/{role}")
async def signaling(ws: WebSocket, request_id: str, role: str):
    item = requests_by_id.get(request_id)
    if not item or item["status"] != "approved" or role not in ("host", "viewer"):
        await ws.close(code=1008)
        return

    await ws.accept()
    room = peers.setdefault(request_id, {})
    if role in room:
        await ws.close(code=1008)
        return
    room[role] = ws
    other_role = "viewer" if role == "host" else "host"

    try:
        other = room.get(other_role)
        if other:
            await other.send_json({"type": "peer_joined"})
        while True:
            message = await ws.receive_text()
            other = room.get(other_role)
            if other:
                await other.send_text(message)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if room.get(role) is ws:
            room.pop(role, None)
        other = room.get(other_role)
        if other:
            try:
                await other.send_json({"type": "peer_disconnected"})
            except Exception:
                pass
        if not room:
            peers.pop(request_id, None)
