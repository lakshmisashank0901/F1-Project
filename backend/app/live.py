import asyncio
import json
from urllib.parse import quote

import httpx
import websockets

from app.feed import decode_compressed, parse_frames

NEGOTIATE_URL = "https://livetiming.formula1.com/signalrcore/negotiate?negotiateVersion=1"
SOCKET_URL = "wss://livetiming.formula1.com/signalrcore"
TOPICS = [
    "Heartbeat",
    "DriverList",
    "SessionInfo",
    "SessionStatus",
    "TimingData",
    "LapCount",
    "Position.z",
]
HANDSHAKE = '{"protocol":"json","version":1}\x1e'


class LiveTiming:
    def __init__(self, state, publish, token):
        self.state = state
        self.publish = publish
        self.token = token
        self.status = "connecting"
        self._dirty = False

    async def run(self):
        flush = asyncio.create_task(self._flush())
        try:
            while True:
                try:
                    self.status = "connecting"
                    await self._publish_now()
                    await self._connect()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self.status = "offline"
                    await self._publish_now()
                    await asyncio.sleep(3)
        finally:
            flush.cancel()

    async def _flush(self):
        while True:
            await asyncio.sleep(0.1)
            if self._dirty:
                self._dirty = False
                await self._publish_now()

    async def _publish_now(self):
        snap = self.state.snapshot()
        snap["status"] = self.status
        snap["preview"] = False
        await self.publish(snap)

    async def _connect(self):
        headers = {
            "User-Agent": "BestHTTP",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            await client.options("https://livetiming.formula1.com/signalrcore/negotiate", headers=headers)
            negotiated = await client.post(NEGOTIATE_URL, headers=headers)
            negotiated.raise_for_status()
            body = negotiated.json()
            connection_id = body.get("connectionToken") or body["connectionId"]
            cookie = "; ".join(f"{name}={value}" for name, value in client.cookies.items())
        socket_headers = dict(headers)
        if cookie:
            socket_headers["Cookie"] = cookie
        url = f"{SOCKET_URL}?id={quote(connection_id, safe='')}"
        async with websockets.connect(url, additional_headers=socket_headers, open_timeout=20, ping_interval=None) as socket:
            await socket.send(HANDSHAKE)
            subscribe = json.dumps(
                {"type": 1, "invocationId": "1", "target": "Subscribe", "arguments": [TOPICS]}
            )
            await socket.send(subscribe + "\x1e")
            self.status = "live"
            buffer = ""
            async for incoming in socket:
                if isinstance(incoming, bytes):
                    incoming = incoming.decode()
                buffer += incoming
                messages, buffer = parse_frames(buffer)
                for message in messages:
                    await self._on_message(socket, message)

    async def _on_message(self, socket, message):
        kind = message.get("type")
        if kind == 6:
            await socket.send('{"type":6}\x1e')
            return
        if kind == 7:
            raise ConnectionError(message.get("error") or "timing stream closed")
        if kind == 3 and isinstance(message.get("result"), dict):
            for topic, payload in message["result"].items():
                self._apply(topic, payload)
            self._dirty = True
            return
        if kind == 1 and message.get("target") == "feed":
            args = message.get("arguments") or []
            if len(args) >= 2:
                self._apply(args[0], args[1])
                self._dirty = True

    def _apply(self, topic, payload):
        if topic == "Position.z" and isinstance(payload, str):
            try:
                payload = decode_compressed(payload)
            except ValueError:
                return
        if topic in {"DriverList", "TimingData", "SessionInfo", "Position.z"}:
            self.state.apply(topic, payload)
