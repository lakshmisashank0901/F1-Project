import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.replay import run_free_replay
from app.state import RaceState


def load_env_file():
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class Hub:
    def __init__(self):
        self.snapshot = {
            "status": "connecting",
            "preview": False,
            "session": {"trackName": "Waiting for session", "location": "", "name": "", "kind": "Other"},
            "raceOrder": [],
            "drivers": [],
            "constructors": [],
            "cars": [],
            "track": [],
        }
        self.version = 0
        self.condition = asyncio.Condition()

    async def publish(self, snapshot):
        async with self.condition:
            self.snapshot = snapshot
            self.version += 1
            self.condition.notify_all()


hub = Hub()
state = RaceState()


async def run_source():
    load_env_file()
    await run_free_replay(state, hub.publish)


@asynccontextmanager
async def lifespan(_app):
    task = asyncio.create_task(run_source())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True, "status": hub.snapshot.get("status")}


@app.websocket("/ws")
async def stream(socket: WebSocket):
    await socket.accept()
    seen = -1
    try:
        while True:
            async with hub.condition:
                await hub.condition.wait_for(lambda: hub.version != seen)
                seen = hub.version
                payload = hub.snapshot
            await socket.send_json(payload)
    except WebSocketDisconnect:
        return
